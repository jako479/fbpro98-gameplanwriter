from __future__ import annotations

import io
import shutil
from pathlib import Path

import pytest
from conftest import OFFENSE_PLN, PLAYPOOL_DIR
from fbpro98_gameplan import read_gameplan

from fbpro98_gameplanwriter.cli import main, parse_args
from fbpro98_gameplanwriter.config import load_config
from fbpro98_gameplanwriter.gameplan_writer import GamePlanWriter

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
    """Same file path for both flags: parsed once, sections dispatched."""
    pln_path = tmp_path / "offense.pln"
    shutil.copy2(OFFENSE_PLN, pln_path)

    combined = tmp_path / "combined.txt"
    combined.write_text(
        "=== Normal ===\nOR45RL01\n=== Special ===\nAF-KO\n",
        encoding="utf-8",
    )

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
    placed = reloaded.custom_special_plays[1]
    assert placed is not None
    assert placed.name.upper() == "AF-KO"


def test_main_only_normal_flag_with_combined_file_ignores_special_section(
    tmp_path: Path,
) -> None:
    pln_path = tmp_path / "offense.pln"
    shutil.copy2(OFFENSE_PLN, pln_path)
    pre_specials = [(p.name if p else None) for p in read_gameplan(pln_path).custom_special_plays]

    combined = tmp_path / "combined.txt"
    combined.write_text(
        "OR45RL01\n=== Special ===\nAF-KO\n",
        encoding="utf-8",
    )

    rc = main(
        [
            str(pln_path),
            "--normal-plays",
            str(combined),
            "--play-path",
            str(PLAYPOOL_DIR),
        ]
    )
    assert rc == 0

    reloaded = read_gameplan(pln_path)
    assert reloaded.normal_plays[0] is not None
    assert reloaded.normal_plays[0].name == "OR45RL01"
    post_specials = [(p.name if p else None) for p in reloaded.custom_special_plays]
    assert post_specials == pre_specials


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

    combined = "=== Normal ===\nOR45RL01\n=== Special ===\nAF-KO\n"
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


def test_main_combined_stdin_with_only_normal_flag_drops_special(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pln_path = tmp_path / "offense.pln"
    shutil.copy2(OFFENSE_PLN, pln_path)
    pre_specials = [(p.name if p else None) for p in read_gameplan(pln_path).custom_special_plays]

    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO("=== Normal ===\nOR45RL01\n=== Special ===\nAF-KO\n"),
    )

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
    post_specials = [(p.name if p else None) for p in reloaded.custom_special_plays]
    assert post_specials == pre_specials
