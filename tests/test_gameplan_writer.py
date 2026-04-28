from __future__ import annotations

import logging
import shutil
from collections.abc import Iterable
from pathlib import Path

import pytest
from conftest import DEFENSE_DIR, DEFENSE_PLN, OFFENSE_DIR, OFFENSE_PLN, PLAYPOOL_DIR
from fbpro98_gameplan import Play, read_gameplan

from pnfl_playpool import PlayPool

from fbpro98_gameplanwriter.gameplan_writer import GamePlanWriter

_pool: PlayPool | None = None


def _get_pool() -> PlayPool:
    global _pool
    if _pool is None:
        _pool = PlayPool.from_directory(PLAYPOOL_DIR)
    return _pool


def _make_writer(pln_path: Path) -> GamePlanWriter:
    return GamePlanWriter(_get_pool(), pln_path)


def _copy_pln(src: Path, tmp_path: Path) -> Path:
    dest = tmp_path / src.name
    shutil.copy2(src, dest)
    return dest


def _write_plays_file(tmp_path: Path, lines: list[str]) -> Path:
    plays_path = tmp_path / "plays.txt"
    plays_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return plays_path


def _filled_count(plays: Iterable[Play | None]) -> int:
    return sum(1 for p in plays if p is not None)


def _filled_names_upper(plays: Iterable[Play | None]) -> set[str]:
    return {p.name.upper() for p in plays if p is not None}


def _get_offensive_names(count: int) -> list[str]:
    pool = PlayPool.from_directory(PLAYPOOL_DIR)
    return [p.name for p in pool.offensive_plays[:count]]


def _get_defensive_names(count: int) -> list[str]:
    pool = PlayPool.from_directory(PLAYPOOL_DIR)
    return [p.name for p in pool.defensive_plays[:count]]


def test_blank_lines_produce_empty_slots(tmp_path: Path) -> None:
    pln_path = _copy_pln(OFFENSE_PLN, tmp_path)
    names = _get_offensive_names(3)
    lines = [names[0], "", names[1], "", "", names[2]]
    plays_path = _write_plays_file(tmp_path, lines)

    writer = _make_writer(pln_path)
    writer.write_from_play_list(plays_path)

    reloaded = read_gameplan(pln_path)
    assert _filled_count(reloaded.normal_plays) == 3
    assert reloaded.normal_plays[0] is not None
    assert reloaded.normal_plays[1] is None
    assert reloaded.normal_plays[2] is not None


def test_lines_beyond_64_ignored_no_blanks(tmp_path: Path) -> None:
    pln_path = _copy_pln(OFFENSE_PLN, tmp_path)
    names = _get_offensive_names(66)
    plays_path = _write_plays_file(tmp_path, names)

    writer = _make_writer(pln_path)
    writer.write_from_play_list(plays_path)

    reloaded = read_gameplan(pln_path)
    assert _filled_count(reloaded.normal_plays) == 64
    reloaded_names = _filled_names_upper(reloaded.normal_plays)
    assert names[64].upper() not in reloaded_names
    assert names[65].upper() not in reloaded_names


def test_lines_beyond_64_ignored_with_blanks(tmp_path: Path) -> None:
    pln_path = _copy_pln(OFFENSE_PLN, tmp_path)
    names = _get_offensive_names(66)
    # 54 plays + 10 blanks + 2 more plays = 66 lines, then 2 plays at lines 65-66
    lines = names[:54] + [""] * 10 + names[54:]
    plays_path = _write_plays_file(tmp_path, lines)

    writer = _make_writer(pln_path)
    writer.write_from_play_list(plays_path)

    reloaded = read_gameplan(pln_path)
    assert _filled_count(reloaded.normal_plays) == 54
    reloaded_names = _filled_names_upper(reloaded.normal_plays)
    for name in names[54:]:
        assert name.upper() not in reloaded_names


def test_unknown_play_name_skipped_with_warning(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    pln_path = _copy_pln(OFFENSE_PLN, tmp_path)
    plays_path = _write_plays_file(tmp_path, ["TOTALLYNOTAPLAY"])

    with caplog.at_level(logging.WARNING):
        writer = _make_writer(pln_path)
        writer.write_from_play_list(plays_path)

    assert "Play not found" in caplog.text
    assert "TOTALLYNOTAPLAY" in caplog.text
    reloaded = read_gameplan(pln_path)
    assert _filled_count(reloaded.normal_plays) == 0


def test_case_insensitive_play_names(tmp_path: Path) -> None:
    pln_path = _copy_pln(OFFENSE_PLN, tmp_path)
    names = _get_offensive_names(1)
    lowercase_names = [n.lower() for n in names]
    plays_path = _write_plays_file(tmp_path, lowercase_names)

    writer = _make_writer(pln_path)
    writer.write_from_play_list(plays_path)

    reloaded = read_gameplan(pln_path)
    assert _filled_count(reloaded.normal_plays) == 1


def test_defensive_play_in_offensive_gameplan_skipped_with_warning(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    pln_path = _copy_pln(OFFENSE_PLN, tmp_path)
    defensive_names = _get_defensive_names(1)
    plays_path = _write_plays_file(tmp_path, defensive_names)

    with caplog.at_level(logging.WARNING):
        writer = _make_writer(pln_path)
        writer.write_from_play_list(plays_path)

    assert "defensive play" in caplog.text
    reloaded = read_gameplan(pln_path)
    assert _filled_count(reloaded.normal_plays) == 0


def test_offensive_play_in_defensive_gameplan_skipped_with_warning(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    pln_path = _copy_pln(DEFENSE_PLN, tmp_path)
    offensive_names = _get_offensive_names(1)
    plays_path = _write_plays_file(tmp_path, offensive_names)

    with caplog.at_level(logging.WARNING):
        writer = _make_writer(pln_path)
        writer.write_from_play_list(plays_path)

    assert "offensive play" in caplog.text
    reloaded = read_gameplan(pln_path)
    assert _filled_count(reloaded.normal_plays) == 0


def test_special_teams_play_skipped_in_offensive_gameplan(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    pln_path = _copy_pln(OFFENSE_PLN, tmp_path)
    plays_path = _write_plays_file(tmp_path, ["AF-KO"])

    with caplog.at_level(logging.WARNING):
        writer = _make_writer(pln_path)
        writer.write_from_play_list(plays_path)

    assert "special teams play" in caplog.text
    reloaded = read_gameplan(pln_path)
    assert _filled_count(reloaded.normal_plays) == 0


def test_special_teams_play_skipped_in_defensive_gameplan(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    pln_path = _copy_pln(DEFENSE_PLN, tmp_path)
    plays_path = _write_plays_file(tmp_path, ["AF-KO"])

    with caplog.at_level(logging.WARNING):
        writer = _make_writer(pln_path)
        writer.write_from_play_list(plays_path)

    assert "special teams play" in caplog.text
    reloaded = read_gameplan(pln_path)
    assert _filled_count(reloaded.normal_plays) == 0


def test_65_plays_with_duplicate_does_not_promote_line_65(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    pln_path = _copy_pln(OFFENSE_PLN, tmp_path)
    names = _get_offensive_names(66)
    # 64 unique plays but slot 1 duplicates slot 0, then play 65 on line 65
    lines = [names[0]] + [names[0]] + names[2:64] + [names[64]]
    assert len(lines) == 65
    plays_path = _write_plays_file(tmp_path, lines)

    with caplog.at_level(logging.WARNING):
        writer = _make_writer(pln_path)
        writer.write_from_play_list(plays_path)

    assert "Duplicate play" in caplog.text
    reloaded = read_gameplan(pln_path)
    assert _filled_count(reloaded.normal_plays) == 63
    reloaded_names = _filled_names_upper(reloaded.normal_plays)
    assert names[64].upper() not in reloaded_names


def test_duplicate_play_skipped_with_warning(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    pln_path = _copy_pln(OFFENSE_PLN, tmp_path)
    names = _get_offensive_names(1)
    lines = [names[0], names[0], names[0]]
    plays_path = _write_plays_file(tmp_path, lines)

    with caplog.at_level(logging.WARNING):
        writer = _make_writer(pln_path)
        writer.write_from_play_list(plays_path)

    assert "Duplicate play" in caplog.text
    assert "slot 1-2 (line 2)" in caplog.text
    assert "already at slot 1-1 (line 1)" in caplog.text
    reloaded = read_gameplan(pln_path)
    assert _filled_count(reloaded.normal_plays) == 1


def _write_dgp(src_pln: Path, plays_txt: Path, tmp_path: Path) -> Path:
    """Copy a .pln to tmp_path and write plays into it."""
    pln_path = _copy_pln(src_pln, tmp_path)
    writer = _make_writer(pln_path)
    writer.write_from_play_list(plays_txt)
    return pln_path


def _assert_matches_expected(pln_path: Path, expected_path: Path) -> None:
    """Byte-for-byte comparison of a written .pln against a game-produced reference."""
    ours = pln_path.read_bytes()
    exp = expected_path.read_bytes()
    assert ours == exp


def _assert_special_plays_preserved(original_path: Path, reloaded_path: Path) -> None:
    original = read_gameplan(original_path)
    reloaded = read_gameplan(reloaded_path)
    for i in range(reloaded.NUMBER_SPECIAL_SLOTS):
        orig_play = original.special_plays[i]
        new_play = reloaded.special_plays[i]
        if orig_play is None:
            assert new_play is None
        else:
            assert new_play is not None
            assert new_play.name == orig_play.name


def test_den_dgp1_update(tmp_path: Path) -> None:
    src_pln = DEFENSE_DIR / "DEN-DGP1.pln"
    plays_txt = DEFENSE_DIR / "DGP1.txt"
    expected = DEFENSE_DIR / "expected" / "DEN-DGP1.pln"

    pln_path = _write_dgp(src_pln, plays_txt, tmp_path)

    reloaded = read_gameplan(pln_path)
    assert reloaded.is_defense
    assert _filled_count(reloaded.normal_plays) == 47

    _assert_special_plays_preserved(src_pln, pln_path)
    _assert_matches_expected(pln_path, expected)


def test_den_dgp2_update(tmp_path: Path) -> None:
    src_pln = DEFENSE_DIR / "DEN-DGP2.pln"
    plays_txt = DEFENSE_DIR / "DGP2.txt"
    expected = DEFENSE_DIR / "expected" / "DEN-DGP2.pln"

    pln_path = _write_dgp(src_pln, plays_txt, tmp_path)

    reloaded = read_gameplan(pln_path)
    assert reloaded.is_defense
    assert _filled_count(reloaded.normal_plays) == 47

    _assert_special_plays_preserved(src_pln, pln_path)
    _assert_matches_expected(pln_path, expected)


def test_den_ogp1_update(tmp_path: Path) -> None:
    src_pln = OFFENSE_DIR / "DEN-OGP1.pln"
    plays_txt = OFFENSE_DIR / "OGP1.txt"
    expected = OFFENSE_DIR / "expected" / "DEN-OGP1.pln"

    pln_path = _write_dgp(src_pln, plays_txt, tmp_path)

    reloaded = read_gameplan(pln_path)
    assert reloaded.is_offense
    assert _filled_count(reloaded.normal_plays) == 64

    _assert_special_plays_preserved(src_pln, pln_path)
    _assert_matches_expected(pln_path, expected)


def test_den_ogp2_update(tmp_path: Path) -> None:
    src_pln = OFFENSE_DIR / "DEN-OGP2.pln"
    plays_txt = OFFENSE_DIR / "OGP2.txt"
    expected = OFFENSE_DIR / "expected" / "DEN-OGP2.pln"

    pln_path = _write_dgp(src_pln, plays_txt, tmp_path)

    reloaded = read_gameplan(pln_path)
    assert reloaded.is_offense
    assert _filled_count(reloaded.normal_plays) == 64

    _assert_special_plays_preserved(src_pln, pln_path)
    _assert_matches_expected(pln_path, expected)
