from __future__ import annotations

import io
import shutil
from pathlib import Path

import pytest
from conftest import OFFENSE_PLN, PLAYPOOL_DIR
from fbpro98_gameplan import read_gameplan

from pnfl_gameplanwriter.cli import main, parse_args
from pnfl_gameplanwriter.config import load_config
from pnfl_gameplanwriter.gameplan_writer import GamePlanWriter

# ---------- argparse ----------


def test_parse_args_requires_gameplan() -> None:
    with pytest.raises(SystemExit):
        parse_args([])


def test_parse_args_requires_at_least_one_plays_flag() -> None:
    with pytest.raises(SystemExit):
        parse_args(["offense.pln"])


def test_parse_args_accepts_normal_only() -> None:
    args = parse_args(["offense.pln", "--normal-plays", "plays.txt"])
    assert args.gameplan_path == "offense.pln"
    assert args.normal_plays == "plays.txt"
    assert args.special_plays is None


def test_parse_args_accepts_special_only() -> None:
    args = parse_args(["offense.pln", "--special-plays", "spec.txt"])
    assert args.normal_plays is None
    assert args.special_plays == "spec.txt"


def test_parse_args_accepts_both_plays() -> None:
    args = parse_args(["offense.pln", "--normal-plays", "n.txt", "--special-plays", "s.txt"])
    assert args.normal_plays == "n.txt"
    assert args.special_plays == "s.txt"


def test_parse_args_accepts_dash_for_normal() -> None:
    args = parse_args(["offense.pln", "--normal-plays", "-"])
    assert args.normal_plays == "-"


def test_parse_args_accepts_dash_for_special() -> None:
    args = parse_args(["offense.pln", "--special-plays", "-"])
    assert args.special_plays == "-"


def test_parse_args_accepts_dash_for_both() -> None:
    args = parse_args(["offense.pln", "--normal-plays", "-", "--special-plays", "-"])
    assert args.normal_plays == "-"
    assert args.special_plays == "-"


def test_parse_args_accepts_play_path_override() -> None:
    args = parse_args(["offense.pln", "--normal-plays", "n.txt", "--play-path", r"E:\PNFL"])
    assert args.play_path == r"E:\PNFL"


def test_parse_args_accepts_config_override() -> None:
    args = parse_args(["offense.pln", "--normal-plays", "n.txt", "--config", "custom.ini"])
    assert args.config == Path("custom.ini")


# ---------- config ----------


def test_config_play_path_override(tmp_path: Path) -> None:
    config_path = tmp_path / "write-gameplan.ini"
    config_path.write_text("[Settings]\nPlayPath=C:\\from-config\n", encoding="utf-8")
    assert load_config(path=config_path).play_path == "C:\\from-config"
    assert load_config(path=config_path, play_path=r"D:\from-cli").play_path == r"D:\from-cli"


def test_config_falls_back_to_defaults(tmp_path: Path) -> None:
    nonexistent = tmp_path / "nonexistent.ini"
    config = load_config(path=nonexistent)
    assert config.play_path == r"C:\SIERRA\FbPro98\PNFL"


def test_from_config_builds_writer(tmp_path: Path) -> None:
    config_path = tmp_path / "test.ini"
    config_path.write_text(f"[Settings]\nPlayPath={PLAYPOOL_DIR}\n", encoding="utf-8")
    config = load_config(path=config_path)
    writer = GamePlanWriter.from_config(config, OFFENSE_PLN)
    assert writer.gameplan_path == OFFENSE_PLN
    assert writer.play_pool is not None


# ---------- main: file input ----------


def test_main_writes_normal_plays_from_file(tmp_path: Path) -> None:
    pln_path = tmp_path / "offense.pln"
    shutil.copy2(OFFENSE_PLN, pln_path)

    plays_txt = tmp_path / "plays.txt"
    plays_txt.write_text("OR45RL01\n", encoding="utf-8")

    rc = main(
        [
            str(pln_path),
            "--normal-plays",
            str(plays_txt),
            "--play-path",
            str(PLAYPOOL_DIR),
        ]
    )
    assert rc == 0

    reloaded = read_gameplan(pln_path)
    assert reloaded.normal_plays[0] is not None
    assert reloaded.normal_plays[0].name == "OR45RL01"
    assert all(p is None for p in reloaded.normal_plays[1:])


def test_main_writes_special_plays_from_file(tmp_path: Path) -> None:
    pln_path = tmp_path / "offense.pln"
    shutil.copy2(OFFENSE_PLN, pln_path)

    spec_txt = tmp_path / "spec.txt"
    spec_txt.write_text("AF-KO\n", encoding="utf-8")

    rc = main(
        [
            str(pln_path),
            "--special-plays",
            str(spec_txt),
            "--play-path",
            str(PLAYPOOL_DIR),
        ]
    )
    assert rc == 0

    reloaded = read_gameplan(pln_path)
    placed = reloaded.custom_special_plays[1]  # Kickoff slot
    assert placed is not None
    assert placed.name.upper() == "AF-KO"


def test_main_writes_both_from_separate_files(tmp_path: Path) -> None:
    pln_path = tmp_path / "offense.pln"
    shutil.copy2(OFFENSE_PLN, pln_path)

    normal_txt = tmp_path / "n.txt"
    normal_txt.write_text("OR45RL01\n", encoding="utf-8")
    spec_txt = tmp_path / "s.txt"
    spec_txt.write_text("AF-KO\n", encoding="utf-8")

    rc = main(
        [
            str(pln_path),
            "--normal-plays",
            str(normal_txt),
            "--special-plays",
            str(spec_txt),
            "--play-path",
            str(PLAYPOOL_DIR),
        ]
    )
    assert rc == 0

    reloaded = read_gameplan(pln_path)
    assert reloaded.normal_plays[0] is not None
    assert reloaded.normal_plays[0].name == "OR45RL01"
    placed = reloaded.custom_special_plays[1]
    assert placed is not None
    assert placed.name.upper() == "AF-KO"


def test_main_combined_file_for_both_flags(tmp_path: Path) -> None:
    """Same file path for both flags: read once, lines [0:64]→normal, [64:74]→special."""
    pln_path = tmp_path / "offense.pln"
    shutil.copy2(OFFENSE_PLN, pln_path)

    normal_lines = ["OR45RL01"] + [""] * 63
    special_lines = ["", "AF-KO"] + [""] * 8
    combined = tmp_path / "combined.txt"
    combined.write_text("\n".join(normal_lines + special_lines) + "\n", encoding="utf-8")

    rc = main(
        [
            str(pln_path),
            "--normal-plays",
            str(combined),
            "--special-plays",
            str(combined),
            "--play-path",
            str(PLAYPOOL_DIR),
        ]
    )
    assert rc == 0

    reloaded = read_gameplan(pln_path)
    assert reloaded.normal_plays[0] is not None
    assert reloaded.normal_plays[0].name == "OR45RL01"
    assert all(p is None for p in reloaded.normal_plays[1:])
    placed = reloaded.custom_special_plays[1]
    assert placed is not None
    assert placed.name.upper() == "AF-KO"
    assert all(p is None for i, p in enumerate(reloaded.custom_special_plays) if i != 1)


def test_main_shared_source_wrong_line_count_raises(tmp_path: Path) -> None:
    pln_path = tmp_path / "offense.pln"
    shutil.copy2(OFFENSE_PLN, pln_path)
    short = tmp_path / "short.txt"
    short.write_text("OR45RL01\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Shared source must have exactly 74 lines"):
        main(
            [
                str(pln_path),
                "--normal-plays",
                str(short),
                "--special-plays",
                str(short),
                "--play-path",
                str(PLAYPOOL_DIR),
            ]
        )


def test_main_normal_plays_over_max_raises(tmp_path: Path) -> None:
    pln_path = tmp_path / "offense.pln"
    shutil.copy2(OFFENSE_PLN, pln_path)
    too_long = tmp_path / "too_long.txt"
    too_long.write_text("OR45RL01\n" * 65, encoding="utf-8")

    with pytest.raises(ValueError, match="--normal-plays source has 65 lines, max is 64"):
        main(
            [
                str(pln_path),
                "--normal-plays",
                str(too_long),
                "--play-path",
                str(PLAYPOOL_DIR),
            ]
        )


def test_main_special_plays_over_max_raises(tmp_path: Path) -> None:
    pln_path = tmp_path / "offense.pln"
    shutil.copy2(OFFENSE_PLN, pln_path)
    too_long = tmp_path / "too_long.txt"
    too_long.write_text("AF-KO\n" * 11, encoding="utf-8")

    with pytest.raises(ValueError, match="--special-plays source has 11 lines, max is 10"):
        main(
            [
                str(pln_path),
                "--special-plays",
                str(too_long),
                "--play-path",
                str(PLAYPOOL_DIR),
            ]
        )


# ---------- main: stdin input ----------


def test_main_reads_normal_from_stdin(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pln_path = tmp_path / "offense.pln"
    shutil.copy2(OFFENSE_PLN, pln_path)

    monkeypatch.setattr("sys.stdin", io.StringIO("OR45RL01\n"))

    rc = main(
        [
            str(pln_path),
            "--normal-plays",
            "-",
            "--play-path",
            str(PLAYPOOL_DIR),
        ]
    )
    assert rc == 0
    reloaded = read_gameplan(pln_path)
    assert reloaded.normal_plays[0] is not None
    assert reloaded.normal_plays[0].name == "OR45RL01"


def test_main_reads_special_from_stdin(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pln_path = tmp_path / "offense.pln"
    shutil.copy2(OFFENSE_PLN, pln_path)

    monkeypatch.setattr("sys.stdin", io.StringIO("AF-KO\n"))

    rc = main(
        [
            str(pln_path),
            "--special-plays",
            "-",
            "--play-path",
            str(PLAYPOOL_DIR),
        ]
    )
    assert rc == 0
    reloaded = read_gameplan(pln_path)
    placed = reloaded.custom_special_plays[1]
    assert placed is not None
    assert placed.name.upper() == "AF-KO"


def test_main_reads_combined_stdin_via_both_dashes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pln_path = tmp_path / "offense.pln"
    shutil.copy2(OFFENSE_PLN, pln_path)

    normal_lines = ["OR45RL01"] + [""] * 63
    special_lines = ["", "AF-KO"] + [""] * 8
    combined = "\n".join(normal_lines + special_lines) + "\n"
    monkeypatch.setattr("sys.stdin", io.StringIO(combined))

    rc = main(
        [
            str(pln_path),
            "--normal-plays",
            "-",
            "--special-plays",
            "-",
            "--play-path",
            str(PLAYPOOL_DIR),
        ]
    )
    assert rc == 0
    reloaded = read_gameplan(pln_path)
    assert reloaded.normal_plays[0] is not None
    assert reloaded.normal_plays[0].name == "OR45RL01"
    placed = reloaded.custom_special_plays[1]
    assert placed is not None
    assert placed.name.upper() == "AF-KO"


def test_main_normal_from_stdin_special_from_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pln_path = tmp_path / "offense.pln"
    shutil.copy2(OFFENSE_PLN, pln_path)

    spec_txt = tmp_path / "s.txt"
    spec_txt.write_text("AF-KO\n", encoding="utf-8")

    monkeypatch.setattr("sys.stdin", io.StringIO("OR45RL01\n"))

    rc = main(
        [
            str(pln_path),
            "--normal-plays",
            "-",
            "--special-plays",
            str(spec_txt),
            "--play-path",
            str(PLAYPOOL_DIR),
        ]
    )
    assert rc == 0
    reloaded = read_gameplan(pln_path)
    assert reloaded.normal_plays[0] is not None
    assert reloaded.normal_plays[0].name == "OR45RL01"
    placed = reloaded.custom_special_plays[1]
    assert placed is not None
    assert placed.name.upper() == "AF-KO"


def test_main_normal_from_file_special_from_stdin(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pln_path = tmp_path / "offense.pln"
    shutil.copy2(OFFENSE_PLN, pln_path)

    normal_txt = tmp_path / "n.txt"
    normal_txt.write_text("OR45RL01\n", encoding="utf-8")

    monkeypatch.setattr("sys.stdin", io.StringIO("AF-KO\n"))

    rc = main(
        [
            str(pln_path),
            "--normal-plays",
            str(normal_txt),
            "--special-plays",
            "-",
            "--play-path",
            str(PLAYPOOL_DIR),
        ]
    )
    assert rc == 0
    reloaded = read_gameplan(pln_path)
    assert reloaded.normal_plays[0] is not None
    assert reloaded.normal_plays[0].name == "OR45RL01"
    placed = reloaded.custom_special_plays[1]
    assert placed is not None
    assert placed.name.upper() == "AF-KO"


# ---------- main: header-bearing input rejection ----------
#
# The reader's default-mode (with `=== Normal ===` / `=== Special ===` headers)
# is human-only and is not consumable by the writer. Piping it in produces
# enough lines to trip the writer's per-flag max-line check, which is the
# correct failure mode (loud, deterministic, and the .pln stays untouched).


def _default_mode_offense_stdout() -> str:
    """The reader's default-mode output for offense.pln (77 lines: 64 + 1 + 1 + 10 + headers)."""
    import io as _io
    import sys as _sys

    from pnfl_gameplanreader.cli import main as reader_main

    buf = _io.StringIO()
    saved = _sys.stdout
    _sys.stdout = buf
    try:
        reader_main([str(OFFENSE_PLN)])
    finally:
        _sys.stdout = saved
    return buf.getvalue()


def test_main_stdin_with_header_rejected_for_normal_plays(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`pnfl read-gameplan src | pnfl write-gameplan dst --normal-plays -` errors."""
    pln_path = tmp_path / "offense.pln"
    shutil.copy2(OFFENSE_PLN, pln_path)

    monkeypatch.setattr("sys.stdin", io.StringIO(_default_mode_offense_stdout()))
    with pytest.raises(ValueError, match=r"--normal-plays source has .* lines, max is 64"):
        main([str(pln_path), "--normal-plays", "-", "--play-path", str(PLAYPOOL_DIR)])


def test_main_stdin_with_header_rejected_for_special_plays(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pln_path = tmp_path / "offense.pln"
    shutil.copy2(OFFENSE_PLN, pln_path)

    monkeypatch.setattr("sys.stdin", io.StringIO(_default_mode_offense_stdout()))
    with pytest.raises(ValueError, match=r"--special-plays source has .* lines, max is 10"):
        main([str(pln_path), "--special-plays", "-", "--play-path", str(PLAYPOOL_DIR)])


def test_main_stdin_with_header_rejected_for_shared_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Both flags as `-` reads stdin once; with-header output has 77 lines, not 74."""
    pln_path = tmp_path / "offense.pln"
    shutil.copy2(OFFENSE_PLN, pln_path)

    monkeypatch.setattr("sys.stdin", io.StringIO(_default_mode_offense_stdout()))
    with pytest.raises(ValueError, match="Shared source must have exactly 74 lines"):
        main(
            [
                str(pln_path),
                "--normal-plays",
                "-",
                "--special-plays",
                "-",
                "--play-path",
                str(PLAYPOOL_DIR),
            ]
        )


def test_main_normal_with_header_special_without_header_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Normal input has a leading header line (65 lines total) — over normal max of 64."""
    pln_path = tmp_path / "offense.pln"
    shutil.copy2(OFFENSE_PLN, pln_path)

    headered_normal = "=== Normal ===\n" + "OR45RL01\n" * 64
    spec_txt = tmp_path / "s.txt"
    spec_txt.write_text("AF-KO\n", encoding="utf-8")
    monkeypatch.setattr("sys.stdin", io.StringIO(headered_normal))

    with pytest.raises(ValueError, match="--normal-plays source has 65 lines, max is 64"):
        main(
            [
                str(pln_path),
                "--normal-plays",
                "-",
                "--special-plays",
                str(spec_txt),
                "--play-path",
                str(PLAYPOOL_DIR),
            ]
        )


def test_main_normal_without_header_special_with_header_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Special input has a leading header line (11 lines total) — over special max of 10."""
    pln_path = tmp_path / "offense.pln"
    shutil.copy2(OFFENSE_PLN, pln_path)

    normal_txt = tmp_path / "n.txt"
    normal_txt.write_text("OR45RL01\n", encoding="utf-8")
    headered_special = "=== Special ===\n" + "AF-KO\n" * 10
    monkeypatch.setattr("sys.stdin", io.StringIO(headered_special))

    with pytest.raises(ValueError, match="--special-plays source has 11 lines, max is 10"):
        main(
            [
                str(pln_path),
                "--normal-plays",
                str(normal_txt),
                "--special-plays",
                "-",
                "--play-path",
                str(PLAYPOOL_DIR),
            ]
        )


# ---------- main: play pool error handling ----------


def test_main_invalid_play_path_logs_error_and_exits_nonzero(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    pln_path = tmp_path / "offense.pln"
    shutil.copy2(OFFENSE_PLN, pln_path)
    plays_txt = tmp_path / "plays.txt"
    plays_txt.write_text("OR45RL01\n", encoding="utf-8")

    bad_path = tmp_path / "does_not_exist"
    with caplog.at_level("ERROR", logger="pnfl_gameplanwriter.cli"):
        exit_code = main(
            [
                str(pln_path),
                "--normal-plays",
                str(plays_txt),
                "--play-path",
                str(bad_path),
            ]
        )
    assert exit_code == 1
    assert "Play pool path does not exist" in caplog.text


def test_main_empty_play_path_raises_value_error(tmp_path: Path) -> None:
    pln_path = tmp_path / "offense.pln"
    shutil.copy2(OFFENSE_PLN, pln_path)
    plays_txt = tmp_path / "plays.txt"
    plays_txt.write_text("OR45RL01\n", encoding="utf-8")

    empty_pool = tmp_path / "empty_pool"
    empty_pool.mkdir()
    with pytest.raises(ValueError, match="contains no plays"):
        main(
            [
                str(pln_path),
                "--normal-plays",
                str(plays_txt),
                "--play-path",
                str(empty_pool),
            ]
        )
