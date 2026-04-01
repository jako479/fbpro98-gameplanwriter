from __future__ import annotations

import logging
import shutil
from pathlib import Path

import pytest

from fbpro98_gameplan import read_gameplan
from fbpro98_gameplanwriter.gameplan_writer import GamePlanWriter


TESTS_DIR = Path(__file__).resolve().parent
DATA_DIR = TESTS_DIR / "data"
PLAYPOOL_DIR = DATA_DIR / "plays"
OFFENSE_PLN = DATA_DIR / "offense.pln"
DEFENSE_PLN = DATA_DIR / "defense.pln"


def _copy_pln(src: Path, tmp_path: Path) -> Path:
    dest = tmp_path / src.name
    shutil.copy2(src, dest)
    return dest


def _write_plays_file(tmp_path: Path, lines: list[str]) -> Path:
    plays_path = tmp_path / "plays.txt"
    plays_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return plays_path


def _get_offensive_names(count: int) -> list[str]:
    from pnfl_playpool import PlayPool
    pool = PlayPool.from_directory(PLAYPOOL_DIR)
    return [p.name for p in pool.offensive_plays[:count]]


def _get_defensive_names(count: int) -> list[str]:
    from pnfl_playpool import PlayPool
    pool = PlayPool.from_directory(PLAYPOOL_DIR)
    return [p.name for p in pool.defensive_plays[:count]]


def test_write_plays_from_text_file(tmp_path: Path) -> None:
    pln_path = _copy_pln(OFFENSE_PLN, tmp_path)
    names = _get_offensive_names(5)
    plays_path = _write_plays_file(tmp_path, names)

    writer = GamePlanWriter(pln_path, PLAYPOOL_DIR)
    writer.write_from_play_list(plays_path)

    reloaded = read_gameplan(pln_path)
    assert len(reloaded.normal_plays) == 5
    reloaded_names = {n.upper() for n in reloaded.normal_plays}
    for name in names:
        assert name.upper() in reloaded_names


def test_blank_lines_produce_empty_slots(tmp_path: Path) -> None:
    pln_path = _copy_pln(OFFENSE_PLN, tmp_path)
    names = _get_offensive_names(3)
    lines = [names[0], "", names[1], "", "", names[2]]
    plays_path = _write_plays_file(tmp_path, lines)

    writer = GamePlanWriter(pln_path, PLAYPOOL_DIR)
    writer.write_from_play_list(plays_path)

    reloaded = read_gameplan(pln_path)
    assert len(reloaded.normal_plays) == 3
    assert 0 in reloaded.plays_by_slot
    assert 1 not in reloaded.plays_by_slot
    assert 2 in reloaded.plays_by_slot


def test_lines_beyond_64_ignored_no_blanks(tmp_path: Path) -> None:
    pln_path = _copy_pln(OFFENSE_PLN, tmp_path)
    names = _get_offensive_names(66)
    plays_path = _write_plays_file(tmp_path, names)

    writer = GamePlanWriter(pln_path, PLAYPOOL_DIR)
    writer.write_from_play_list(plays_path)

    reloaded = read_gameplan(pln_path)
    assert len(reloaded.normal_plays) == 64
    reloaded_names = {n.upper() for n in reloaded.normal_plays}
    assert names[64].upper() not in reloaded_names
    assert names[65].upper() not in reloaded_names


def test_lines_beyond_64_ignored_with_blanks(tmp_path: Path) -> None:
    pln_path = _copy_pln(OFFENSE_PLN, tmp_path)
    names = _get_offensive_names(66)
    # 54 plays + 10 blanks + 2 more plays = 66 lines, then 2 plays at lines 65-66
    lines = names[:54] + [""] * 10 + names[54:]
    plays_path = _write_plays_file(tmp_path, lines)

    writer = GamePlanWriter(pln_path, PLAYPOOL_DIR)
    writer.write_from_play_list(plays_path)

    reloaded = read_gameplan(pln_path)
    assert len(reloaded.normal_plays) == 54
    reloaded_names = {n.upper() for n in reloaded.normal_plays}
    for name in names[54:]:
        assert name.upper() not in reloaded_names


def test_fewer_than_64_pads_empty(tmp_path: Path) -> None:
    pln_path = _copy_pln(OFFENSE_PLN, tmp_path)
    names = _get_offensive_names(2)
    plays_path = _write_plays_file(tmp_path, names)

    writer = GamePlanWriter(pln_path, PLAYPOOL_DIR)
    writer.write_from_play_list(plays_path)

    reloaded = read_gameplan(pln_path)
    assert len(reloaded.normal_plays) == 2
    for slot in range(2, 64):
        assert slot not in reloaded.plays_by_slot


def test_unknown_play_name_skipped_with_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture,
) -> None:
    pln_path = _copy_pln(OFFENSE_PLN, tmp_path)
    plays_path = _write_plays_file(tmp_path, ["TOTALLYNOTAPLAY"])

    with caplog.at_level(logging.WARNING):
        writer = GamePlanWriter(pln_path, PLAYPOOL_DIR)
        writer.write_from_play_list(plays_path)

    assert "Play not found" in caplog.text
    assert "TOTALLYNOTAPLAY" in caplog.text
    reloaded = read_gameplan(pln_path)
    assert len(reloaded.normal_plays) == 0


def test_special_plays_preserved_after_write(tmp_path: Path) -> None:
    pln_path = _copy_pln(OFFENSE_PLN, tmp_path)
    original = read_gameplan(pln_path)
    names = _get_offensive_names(3)
    plays_path = _write_plays_file(tmp_path, names)

    writer = GamePlanWriter(pln_path, PLAYPOOL_DIR)
    writer.write_from_play_list(plays_path)

    reloaded = read_gameplan(pln_path)
    for slot in range(64, 84):
        orig_play = original.plays_by_slot.get(slot)
        new_play = reloaded.plays_by_slot.get(slot)
        if orig_play is None:
            assert new_play is None
        else:
            assert new_play is not None
            assert new_play.name == orig_play.name


def test_case_insensitive_play_names(tmp_path: Path) -> None:
    pln_path = _copy_pln(OFFENSE_PLN, tmp_path)
    names = _get_offensive_names(1)
    lowercase_names = [n.lower() for n in names]
    plays_path = _write_plays_file(tmp_path, lowercase_names)

    writer = GamePlanWriter(pln_path, PLAYPOOL_DIR)
    writer.write_from_play_list(plays_path)

    reloaded = read_gameplan(pln_path)
    assert len(reloaded.normal_plays) == 1


def test_defensive_play_in_offensive_gameplan_skipped_with_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture,
) -> None:
    pln_path = _copy_pln(OFFENSE_PLN, tmp_path)
    defensive_names = _get_defensive_names(1)
    plays_path = _write_plays_file(tmp_path, defensive_names)

    with caplog.at_level(logging.WARNING):
        writer = GamePlanWriter(pln_path, PLAYPOOL_DIR)
        writer.write_from_play_list(plays_path)

    assert "defensive play" in caplog.text
    reloaded = read_gameplan(pln_path)
    assert len(reloaded.normal_plays) == 0


def test_offensive_play_in_defensive_gameplan_skipped_with_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture,
) -> None:
    pln_path = _copy_pln(DEFENSE_PLN, tmp_path)
    offensive_names = _get_offensive_names(1)
    plays_path = _write_plays_file(tmp_path, offensive_names)

    with caplog.at_level(logging.WARNING):
        writer = GamePlanWriter(pln_path, PLAYPOOL_DIR)
        writer.write_from_play_list(plays_path)

    assert "offensive play" in caplog.text
    reloaded = read_gameplan(pln_path)
    assert len(reloaded.normal_plays) == 0


def test_defensive_plays_write_to_defensive_gameplan(tmp_path: Path) -> None:
    pln_path = _copy_pln(DEFENSE_PLN, tmp_path)
    names = _get_defensive_names(3)
    plays_path = _write_plays_file(tmp_path, names)

    writer = GamePlanWriter(pln_path, PLAYPOOL_DIR)
    writer.write_from_play_list(plays_path)

    reloaded = read_gameplan(pln_path)
    assert len(reloaded.normal_plays) == 3


def test_special_teams_play_skipped_in_offensive_gameplan(
    tmp_path: Path, caplog: pytest.LogCaptureFixture,
) -> None:
    pln_path = _copy_pln(OFFENSE_PLN, tmp_path)
    plays_path = _write_plays_file(tmp_path, ["AF-KO"])

    with caplog.at_level(logging.WARNING):
        writer = GamePlanWriter(pln_path, PLAYPOOL_DIR)
        writer.write_from_play_list(plays_path)

    assert "special teams play" in caplog.text
    reloaded = read_gameplan(pln_path)
    assert len(reloaded.normal_plays) == 0


def test_special_teams_play_skipped_in_defensive_gameplan(
    tmp_path: Path, caplog: pytest.LogCaptureFixture,
) -> None:
    pln_path = _copy_pln(DEFENSE_PLN, tmp_path)
    plays_path = _write_plays_file(tmp_path, ["AF-KO"])

    with caplog.at_level(logging.WARNING):
        writer = GamePlanWriter(pln_path, PLAYPOOL_DIR)
        writer.write_from_play_list(plays_path)

    assert "special teams play" in caplog.text
    reloaded = read_gameplan(pln_path)
    assert len(reloaded.normal_plays) == 0


def test_65_plays_with_duplicate_does_not_promote_line_65(
    tmp_path: Path, caplog: pytest.LogCaptureFixture,
) -> None:
    pln_path = _copy_pln(OFFENSE_PLN, tmp_path)
    names = _get_offensive_names(66)
    # 64 unique plays but slot 1 duplicates slot 0, then play 65 on line 65
    lines = [names[0]] + [names[0]] + names[2:64] + [names[64]]
    assert len(lines) == 65
    plays_path = _write_plays_file(tmp_path, lines)

    with caplog.at_level(logging.WARNING):
        writer = GamePlanWriter(pln_path, PLAYPOOL_DIR)
        writer.write_from_play_list(plays_path)

    assert "Duplicate play" in caplog.text
    reloaded = read_gameplan(pln_path)
    assert len(reloaded.normal_plays) == 63
    reloaded_names = {n.upper() for n in reloaded.normal_plays}
    assert names[64].upper() not in reloaded_names


def test_duplicate_play_skipped_with_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture,
) -> None:
    pln_path = _copy_pln(OFFENSE_PLN, tmp_path)
    names = _get_offensive_names(1)
    lines = [names[0], names[0], names[0]]
    plays_path = _write_plays_file(tmp_path, lines)

    with caplog.at_level(logging.WARNING):
        writer = GamePlanWriter(pln_path, PLAYPOOL_DIR)
        writer.write_from_play_list(plays_path)

    assert "Duplicate play" in caplog.text
    assert "slot 1-2 (line 2)" in caplog.text
    assert "already at slot 1-1 (line 1)" in caplog.text
    reloaded = read_gameplan(pln_path)
    assert len(reloaded.normal_plays) == 1
