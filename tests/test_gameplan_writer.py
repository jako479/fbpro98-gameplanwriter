from __future__ import annotations

import logging
import shutil
from collections.abc import Iterable
from pathlib import Path

import pytest
from conftest import DEFENSE_DIR, DEFENSE_PLN, OFFENSE_DIR, OFFENSE_PLN, PLAYPOOL_DIR
from fbpro98_gameplan import CustomPlay, Play, read_gameplan
from fbpro98_play import PlayFile
from pnfl_playpool import PlayPool, SpecialTeamsPlayRecord

from fbpro98_gameplanwriter.gameplan_writer import (
    GamePlanWriter,
    parse_sections,
)

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


# ---------- parse_sections ----------


def test_parse_sections_no_markers_all_normal() -> None:
    text = "AAA\nBBB\nCCC\n"
    s = parse_sections(text)
    assert s["normal"] == ["AAA", "BBB", "CCC"]
    assert s["special"] == []


def test_parse_sections_special_marker_switches_section() -> None:
    text = "AAA\n=== Special ===\nXXX\nYYY\n"
    s = parse_sections(text)
    assert s["normal"] == ["AAA"]
    assert s["special"] == ["XXX", "YYY"]


def test_parse_sections_normal_marker_returns_to_normal() -> None:
    text = "=== Special ===\nSP1\n=== Normal ===\nNRM\n"
    s = parse_sections(text)
    assert s["normal"] == ["NRM"]
    assert s["special"] == ["SP1"]


def test_parse_sections_blank_lines_preserved_in_section() -> None:
    text = "AAA\n\nBBB\n=== Special ===\n\nXXX\n"
    s = parse_sections(text)
    assert s["normal"] == ["AAA", "", "BBB"]
    assert s["special"] == ["", "XXX"]


def test_parse_sections_markers_case_insensitive_and_whitespace_tolerant() -> None:
    text = "  === NORMAL ===  \nAAA\n=== special ===\nXXX\n"
    s = parse_sections(text)
    assert s["normal"] == ["AAA"]
    assert s["special"] == ["XXX"]


def test_parse_sections_decorative_normal_marker_at_start() -> None:
    text = "=== Normal ===\nAAA\nBBB\n=== Special ===\nXXX\n"
    s = parse_sections(text)
    assert s["normal"] == ["AAA", "BBB"]
    assert s["special"] == ["XXX"]


def test_parse_sections_empty_input() -> None:
    s = parse_sections("")
    assert s == {"normal": [], "special": []}


# ---------- normal play behavior (preserved from prior test suite) ----------


def test_blank_lines_produce_empty_slots(tmp_path: Path) -> None:
    pln_path = _copy_pln(OFFENSE_PLN, tmp_path)
    names = _get_offensive_names(3)
    lines = [names[0], "", names[1], "", "", names[2]]

    writer = _make_writer(pln_path)
    writer.write(normal_lines=lines)

    reloaded = read_gameplan(pln_path)
    assert _filled_count(reloaded.normal_plays) == 3
    assert reloaded.normal_plays[0] is not None
    assert reloaded.normal_plays[1] is None
    assert reloaded.normal_plays[2] is not None


def test_lines_beyond_64_ignored_no_blanks(tmp_path: Path) -> None:
    pln_path = _copy_pln(OFFENSE_PLN, tmp_path)
    names = _get_offensive_names(66)

    writer = _make_writer(pln_path)
    writer.write(normal_lines=names)

    reloaded = read_gameplan(pln_path)
    assert _filled_count(reloaded.normal_plays) == 64
    reloaded_names = _filled_names_upper(reloaded.normal_plays)
    assert names[64].upper() not in reloaded_names
    assert names[65].upper() not in reloaded_names


def test_lines_beyond_64_ignored_with_blanks(tmp_path: Path) -> None:
    pln_path = _copy_pln(OFFENSE_PLN, tmp_path)
    names = _get_offensive_names(66)
    lines = names[:54] + [""] * 10 + names[54:]

    writer = _make_writer(pln_path)
    writer.write(normal_lines=lines)

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

    with caplog.at_level(logging.WARNING):
        writer = _make_writer(pln_path)
        writer.write(normal_lines=["TOTALLYNOTAPLAY"])

    assert "Play not found" in caplog.text
    assert "TOTALLYNOTAPLAY" in caplog.text
    reloaded = read_gameplan(pln_path)
    assert _filled_count(reloaded.normal_plays) == 0


def test_case_insensitive_play_names(tmp_path: Path) -> None:
    pln_path = _copy_pln(OFFENSE_PLN, tmp_path)
    names = _get_offensive_names(1)

    writer = _make_writer(pln_path)
    writer.write(normal_lines=[n.lower() for n in names])

    reloaded = read_gameplan(pln_path)
    assert _filled_count(reloaded.normal_plays) == 1


def test_defensive_play_in_offensive_gameplan_skipped_with_warning(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    pln_path = _copy_pln(OFFENSE_PLN, tmp_path)
    defensive_names = _get_defensive_names(1)

    with caplog.at_level(logging.WARNING):
        writer = _make_writer(pln_path)
        writer.write(normal_lines=defensive_names)

    assert "defensive play" in caplog.text
    reloaded = read_gameplan(pln_path)
    assert _filled_count(reloaded.normal_plays) == 0


def test_offensive_play_in_defensive_gameplan_skipped_with_warning(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    pln_path = _copy_pln(DEFENSE_PLN, tmp_path)
    offensive_names = _get_offensive_names(1)

    with caplog.at_level(logging.WARNING):
        writer = _make_writer(pln_path)
        writer.write(normal_lines=offensive_names)

    assert "offensive play" in caplog.text
    reloaded = read_gameplan(pln_path)
    assert _filled_count(reloaded.normal_plays) == 0


def test_special_teams_play_skipped_in_normal_offensive_input(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    pln_path = _copy_pln(OFFENSE_PLN, tmp_path)

    with caplog.at_level(logging.WARNING):
        writer = _make_writer(pln_path)
        writer.write(normal_lines=["AF-KO"])

    assert "special teams play" in caplog.text
    reloaded = read_gameplan(pln_path)
    assert _filled_count(reloaded.normal_plays) == 0


def test_special_teams_play_skipped_in_normal_defensive_input(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    pln_path = _copy_pln(DEFENSE_PLN, tmp_path)

    with caplog.at_level(logging.WARNING):
        writer = _make_writer(pln_path)
        writer.write(normal_lines=["AF-KO"])

    assert "special teams play" in caplog.text
    reloaded = read_gameplan(pln_path)
    assert _filled_count(reloaded.normal_plays) == 0


def test_65_plays_with_duplicate_does_not_promote_line_65(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    pln_path = _copy_pln(OFFENSE_PLN, tmp_path)
    names = _get_offensive_names(66)
    lines = [names[0]] + [names[0]] + names[2:64] + [names[64]]
    assert len(lines) == 65

    with caplog.at_level(logging.WARNING):
        writer = _make_writer(pln_path)
        writer.write(normal_lines=lines)

    assert "Duplicate play" in caplog.text
    reloaded = read_gameplan(pln_path)
    assert _filled_count(reloaded.normal_plays) == 63
    reloaded_names = _filled_names_upper(reloaded.normal_plays)
    assert names[64].upper() not in reloaded_names


def test_duplicate_normal_play_skipped_with_warning(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    pln_path = _copy_pln(OFFENSE_PLN, tmp_path)
    names = _get_offensive_names(1)

    with caplog.at_level(logging.WARNING):
        writer = _make_writer(pln_path)
        writer.write(normal_lines=[names[0], names[0], names[0]])

    assert "Duplicate play" in caplog.text
    assert "slot 1-2 (line 2)" in caplog.text
    assert "already at slot 1-1 (line 1)" in caplog.text
    reloaded = read_gameplan(pln_path)
    assert _filled_count(reloaded.normal_plays) == 1


# ---------- byte-compare integration (normal-only, special preserved) ----------


def _assert_matches_expected(pln_path: Path, expected_path: Path) -> None:
    assert pln_path.read_bytes() == expected_path.read_bytes()


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


def _write_normal_from_file(src_pln: Path, plays_txt: Path, tmp_path: Path) -> Path:
    pln_path = _copy_pln(src_pln, tmp_path)
    writer = _make_writer(pln_path)
    writer.write(normal_lines=plays_txt.read_text(encoding="utf-8").splitlines())
    return pln_path


def test_den_dgp1_update(tmp_path: Path) -> None:
    src_pln = DEFENSE_DIR / "DEN-DGP1.pln"
    plays_txt = DEFENSE_DIR / "DGP1.txt"
    expected = DEFENSE_DIR / "expected" / "DEN-DGP1.pln"
    pln_path = _write_normal_from_file(src_pln, plays_txt, tmp_path)
    reloaded = read_gameplan(pln_path)
    assert reloaded.is_defense
    assert _filled_count(reloaded.normal_plays) == 47
    _assert_special_plays_preserved(src_pln, pln_path)
    _assert_matches_expected(pln_path, expected)


def test_den_dgp2_update(tmp_path: Path) -> None:
    src_pln = DEFENSE_DIR / "DEN-DGP2.pln"
    plays_txt = DEFENSE_DIR / "DGP2.txt"
    expected = DEFENSE_DIR / "expected" / "DEN-DGP2.pln"
    pln_path = _write_normal_from_file(src_pln, plays_txt, tmp_path)
    reloaded = read_gameplan(pln_path)
    assert reloaded.is_defense
    assert _filled_count(reloaded.normal_plays) == 47
    _assert_special_plays_preserved(src_pln, pln_path)
    _assert_matches_expected(pln_path, expected)


def test_den_ogp1_update(tmp_path: Path) -> None:
    src_pln = OFFENSE_DIR / "DEN-OGP1.pln"
    plays_txt = OFFENSE_DIR / "OGP1.txt"
    expected = OFFENSE_DIR / "expected" / "DEN-OGP1.pln"
    pln_path = _write_normal_from_file(src_pln, plays_txt, tmp_path)
    reloaded = read_gameplan(pln_path)
    assert reloaded.is_offense
    assert _filled_count(reloaded.normal_plays) == 64
    _assert_special_plays_preserved(src_pln, pln_path)
    _assert_matches_expected(pln_path, expected)


def test_den_ogp2_update(tmp_path: Path) -> None:
    src_pln = OFFENSE_DIR / "DEN-OGP2.pln"
    plays_txt = OFFENSE_DIR / "OGP2.txt"
    expected = OFFENSE_DIR / "expected" / "DEN-OGP2.pln"
    pln_path = _write_normal_from_file(src_pln, plays_txt, tmp_path)
    reloaded = read_gameplan(pln_path)
    assert reloaded.is_offense
    assert _filled_count(reloaded.normal_plays) == 64
    _assert_special_plays_preserved(src_pln, pln_path)
    _assert_matches_expected(pln_path, expected)


# ---------- special play behavior ----------


def _kickoff_slot_index() -> int:
    """AF-KO has special_category=2 (Kickoff), so slot index 1."""
    return 1


def test_special_play_lands_in_correct_slot(tmp_path: Path) -> None:
    pln_path = _copy_pln(OFFENSE_PLN, tmp_path)
    writer = _make_writer(pln_path)
    writer.write(special_lines=["AF-KO"])

    reloaded = read_gameplan(pln_path)
    custom = reloaded.custom_special_plays
    placed = custom[_kickoff_slot_index()]
    assert placed is not None
    assert placed.name.upper() == "AF-KO"
    for i, play in enumerate(custom):
        if i != _kickoff_slot_index():
            assert play is None


def test_special_blank_lines_skipped(tmp_path: Path) -> None:
    pln_path = _copy_pln(OFFENSE_PLN, tmp_path)
    writer = _make_writer(pln_path)
    writer.write(special_lines=["", "AF-KO", "", ""])

    reloaded = read_gameplan(pln_path)
    custom = reloaded.custom_special_plays
    assert sum(1 for p in custom if p is not None) == 1
    assert custom[_kickoff_slot_index()] is not None


def test_special_unknown_name_skipped_with_warning(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    pln_path = _copy_pln(OFFENSE_PLN, tmp_path)
    with caplog.at_level(logging.WARNING):
        writer = _make_writer(pln_path)
        writer.write(special_lines=["NOSUCHKICK"])
    assert "Special play not found" in caplog.text
    assert "NOSUCHKICK" in caplog.text
    reloaded = read_gameplan(pln_path)
    assert all(p is None for p in reloaded.custom_special_plays)


def test_normal_play_in_special_input_skipped_with_warning(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    pln_path = _copy_pln(OFFENSE_PLN, tmp_path)
    with caplog.at_level(logging.WARNING):
        writer = _make_writer(pln_path)
        writer.write(special_lines=[_get_offensive_names(1)[0]])
    assert "is not a special teams play" in caplog.text
    reloaded = read_gameplan(pln_path)
    assert all(p is None for p in reloaded.custom_special_plays)


def test_duplicate_special_play_skipped_with_warning(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    pln_path = _copy_pln(OFFENSE_PLN, tmp_path)
    with caplog.at_level(logging.WARNING):
        writer = _make_writer(pln_path)
        writer.write(special_lines=["AF-KO", "af-ko"])
    assert "Duplicate special play" in caplog.text
    reloaded = read_gameplan(pln_path)
    assert sum(1 for p in reloaded.custom_special_plays if p is not None) == 1


def test_offense_special_in_defense_gameplan_skipped_with_warning(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    pln_path = _copy_pln(DEFENSE_PLN, tmp_path)
    with caplog.at_level(logging.WARNING):
        writer = _make_writer(pln_path)
        writer.write(special_lines=["AF-KO"])
    assert "offensive special play but gameplan is defensive" in caplog.text
    reloaded = read_gameplan(pln_path)
    assert all(p is None for p in reloaded.custom_special_plays)


def test_duplicate_special_category_skipped_with_warning(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Two distinct play names that happen to share special_category=2.

    Built by stubbing the play pool with synthetic SpecialTeamsPlayRecord
    instances backed by the same on-disk AF-KO.ply (same special_category=2).
    """
    pln_path = _copy_pln(OFFENSE_PLN, tmp_path)
    af_ko_path = PLAYPOOL_DIR / "Special" / "AF-KO.ply"
    play_file = PlayFile.from_file(af_ko_path)

    pool = PlayPool(PLAYPOOL_DIR)
    rec_a = SpecialTeamsPlayRecord(name="AF-KO", play_file=play_file)
    rec_b = SpecialTeamsPlayRecord(name="ALT-KO", play_file=play_file)
    pool._plays_by_name = {"AF-KO": rec_a, "ALT-KO": rec_b}  # type: ignore[attr-defined]

    writer = GamePlanWriter(pool, pln_path)
    with caplog.at_level(logging.WARNING):
        writer.write(special_lines=["AF-KO", "ALT-KO"])

    assert "already filled by another play" in caplog.text
    reloaded = read_gameplan(pln_path)
    custom = reloaded.custom_special_plays
    filled = [p.name for p in custom if p is not None]
    assert filled == ["AF-KO"]


def test_special_only_leaves_normal_unchanged(tmp_path: Path) -> None:
    pln_path = _copy_pln(OFFENSE_DIR / "DEN-OGP1.pln", tmp_path)
    original = read_gameplan(pln_path)
    original_normal_names = [(p.name if p is not None else None) for p in original.normal_plays]

    writer = _make_writer(pln_path)
    writer.write(special_lines=["AF-KO"])

    reloaded = read_gameplan(pln_path)
    reloaded_normal_names = [(p.name if p is not None else None) for p in reloaded.normal_plays]
    assert reloaded_normal_names == original_normal_names
    placed = reloaded.custom_special_plays[_kickoff_slot_index()]
    assert placed is not None
    assert placed.name.upper() == "AF-KO"


def test_normal_only_leaves_special_unchanged(tmp_path: Path) -> None:
    pln_path = _copy_pln(OFFENSE_DIR / "DEN-OGP1.pln", tmp_path)
    original = read_gameplan(pln_path)
    original_special_names = [(p.name if p is not None else None) for p in original.custom_special_plays]

    names = _get_offensive_names(3)
    writer = _make_writer(pln_path)
    writer.write(normal_lines=names)

    reloaded = read_gameplan(pln_path)
    reloaded_special_names = [(p.name if p is not None else None) for p in reloaded.custom_special_plays]
    assert reloaded_special_names == original_special_names


def test_both_normal_and_special_applied_together(tmp_path: Path) -> None:
    pln_path = _copy_pln(OFFENSE_PLN, tmp_path)
    names = _get_offensive_names(2)

    writer = _make_writer(pln_path)
    writer.write(normal_lines=names, special_lines=["AF-KO"])

    reloaded = read_gameplan(pln_path)
    assert _filled_count(reloaded.normal_plays) == 2
    placed = reloaded.custom_special_plays[_kickoff_slot_index()]
    assert placed is not None
    assert placed.name.upper() == "AF-KO"


def test_empty_special_list_clears_all_custom_special_slots(tmp_path: Path) -> None:
    pln_path = _copy_pln(OFFENSE_DIR / "DEN-OGP1.pln", tmp_path)
    pre = read_gameplan(pln_path)
    assert any(p is not None for p in pre.custom_special_plays)

    writer = _make_writer(pln_path)
    writer.write(special_lines=[])

    reloaded = read_gameplan(pln_path)
    assert all(p is None for p in reloaded.custom_special_plays)


def test_special_play_filename_uses_pnfl_prefix(tmp_path: Path) -> None:
    pln_path = _copy_pln(OFFENSE_PLN, tmp_path)
    writer = _make_writer(pln_path)
    writer.write(special_lines=["AF-KO"])
    reloaded = read_gameplan(pln_path)
    play = reloaded.custom_special_plays[_kickoff_slot_index()]
    assert isinstance(play, CustomPlay)
    assert play.filename.startswith("PNFL\\")
    assert play.filename.endswith("AF-KO.ply")
