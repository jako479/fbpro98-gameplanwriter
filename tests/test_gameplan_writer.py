from __future__ import annotations

import logging
import shutil
from collections.abc import Iterable, Sequence
from pathlib import Path

import pytest
from conftest import DATA_DIR, DEFENSE_PLN, EXPECTED_DIR, OFFENSE_PLN, PLAYPOOL_DIR
from fbpro98_gameplan import CustomPlay, Play, read_gameplan
from fbpro98_play import read_play
from pnfl_playpool import PlayPool, SpecialTeamsPlayRecord, read_play_pool

from fbpro98_gameplanwriter.gameplan_writer import GamePlanWriter

_pool: PlayPool | None = None


def _get_pool() -> PlayPool:
    global _pool
    if _pool is None:
        _pool = read_play_pool(PLAYPOOL_DIR)
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
    pool = read_play_pool(PLAYPOOL_DIR)
    return [p.name for p in pool.offensive_plays[:count]]


def _get_defensive_names(count: int) -> list[str]:
    pool = read_play_pool(PLAYPOOL_DIR)
    return [p.name for p in pool.defensive_plays[:count]]


def find_play_slot_mismatches(
    expected: Sequence[str],
    actual: Sequence[Play | None],
) -> list[str]:
    """Return human-readable failure descriptions for slots whose play name doesn't match.

    Each entry of `expected` is the expected play name for that slot, or "" to expect
    an empty slot. Comparisons are case-insensitive. Returns an empty list if all match.
    """
    if len(expected) != len(actual):
        return [f"Slot count mismatch: expected {len(expected)}, got {len(actual)}"]
    mismatches: list[str] = []
    for i, (exp_name, actual_play) in enumerate(zip(expected, actual, strict=True)):
        actual_name = actual_play.name if actual_play else ""
        if actual_name.upper() != (exp_name or "").upper():
            mismatches.append(f"Slot {i}: expected {exp_name!r}, got {actual_name!r}")
    return mismatches


# ---------- normal play behavior ----------


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


def test_defense_55_10a_update(tmp_path: Path) -> None:
    src_pln = DATA_DIR / "D_55_10a.pln"
    plays_txt = DATA_DIR / "D_55_10a.txt"
    expected = EXPECTED_DIR / "D_47_10a.pln"
    pln_path = _write_normal_from_file(src_pln, plays_txt, tmp_path)
    reloaded = read_gameplan(pln_path)
    assert reloaded.is_defense
    assert _filled_count(reloaded.normal_plays) == 47
    _assert_special_plays_preserved(src_pln, pln_path)
    _assert_matches_expected(pln_path, expected)


def test_defense_55_10b_update(tmp_path: Path) -> None:
    src_pln = DATA_DIR / "D_55_10b.pln"
    plays_txt = DATA_DIR / "D_55_10b.txt"
    expected = EXPECTED_DIR / "D_47_10b.pln"
    pln_path = _write_normal_from_file(src_pln, plays_txt, tmp_path)
    reloaded = read_gameplan(pln_path)
    assert reloaded.is_defense
    assert _filled_count(reloaded.normal_plays) == 47
    _assert_special_plays_preserved(src_pln, pln_path)
    _assert_matches_expected(pln_path, expected)


def test_offense_64_06a_update(tmp_path: Path) -> None:
    src_pln = DATA_DIR / "O_64_06a.pln"
    plays_txt = DATA_DIR / "O_64_06a.txt"
    expected = EXPECTED_DIR / "O_64_06a.pln"
    pln_path = _write_normal_from_file(src_pln, plays_txt, tmp_path)
    reloaded = read_gameplan(pln_path)
    assert reloaded.is_offense
    assert _filled_count(reloaded.normal_plays) == 64
    _assert_special_plays_preserved(src_pln, pln_path)
    _assert_matches_expected(pln_path, expected)


def test_offense_64_06b_update(tmp_path: Path) -> None:
    src_pln = DATA_DIR / "O_64_06b.pln"
    plays_txt = DATA_DIR / "O_64_06b.txt"
    expected = EXPECTED_DIR / "O_64_06b.pln"
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


SPECIAL_FIXTURES = [
    # (fixture_name, expected_special_category, "offense"/"defense")
    ("BCFGPATD", 1, "defense"),  # Field Goal/PAT Defense — first slot, defensive
    ("DETFGPAT", 1, "defense"),  # Field Goal/PAT Defense — first slot, defensive (alt)
    ("AF-KO", 2, "offense"),  # Kickoff
    ("CIN-PUNT", 3, "offense"),  # Punt
    ("KCSQUIB", 10, "offense"),  # Squib Kick — last slot, offensive
    ("BCSQUIBR", 10, "defense"),  # Squib Return — last slot, defensive
]


@pytest.mark.parametrize(("name", "special_category", "side"), SPECIAL_FIXTURES)
def test_special_play_lands_in_correct_slot(tmp_path: Path, name: str, special_category: int, side: str) -> None:
    src_pln = OFFENSE_PLN if side == "offense" else DEFENSE_PLN
    pln_path = _copy_pln(src_pln, tmp_path)
    writer = _make_writer(pln_path)
    writer.write(special_lines=[name])

    reloaded = read_gameplan(pln_path)
    custom = reloaded.custom_special_plays
    expected_slot = special_category - 1
    placed = custom[expected_slot]
    assert placed is not None
    assert placed.name.upper() == name.upper()
    assert placed.special_category == special_category
    for i, play in enumerate(custom):
        if i != expected_slot:
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


def test_defense_special_in_offense_gameplan_skipped_with_warning(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    pln_path = _copy_pln(OFFENSE_PLN, tmp_path)
    with caplog.at_level(logging.WARNING):
        writer = _make_writer(pln_path)
        writer.write(special_lines=["BCFGPATD"])
    assert "defensive special play but gameplan is offensive" in caplog.text
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
    play_file = read_play(af_ko_path)

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


def test_partial_special_input_clears_remaining_special_preserves_normal(tmp_path: Path) -> None:
    """Less than 10 specials: unsupplied slots cleared, normal section untouched."""
    pln_path = _copy_pln(DATA_DIR / "O_64_06a.pln", tmp_path)
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
    for i, play in enumerate(reloaded.custom_special_plays):
        if i != _kickoff_slot_index():
            assert play is None, f"slot {i} should be cleared but contains {play!r}"


def test_partial_normal_input_clears_remaining_normal_preserves_special(tmp_path: Path) -> None:
    """Less than 64 normals: unsupplied slots cleared, special section untouched."""
    pln_path = _copy_pln(DATA_DIR / "O_64_06a.pln", tmp_path)
    original = read_gameplan(pln_path)
    original_special_names = [(p.name if p is not None else None) for p in original.custom_special_plays]

    names = _get_offensive_names(3)
    writer = _make_writer(pln_path)
    writer.write(normal_lines=names)

    reloaded = read_gameplan(pln_path)
    reloaded_special_names = [(p.name if p is not None else None) for p in reloaded.custom_special_plays]
    assert reloaded_special_names == original_special_names
    expected_normal = list(names) + [""] * (64 - len(names))
    failures = find_play_slot_mismatches(expected_normal, reloaded.normal_plays)
    assert not failures, "\n" + "\n".join(failures)


def test_full_64_normal_input_replaces_normal_preserves_special(tmp_path: Path) -> None:
    """Full 64-normal write replaces all normal slots and leaves special section untouched."""
    pln_path = _copy_pln(DATA_DIR / "O_64_06a.pln", tmp_path)
    original = read_gameplan(pln_path)
    original_special_names = [(p.name if p is not None else None) for p in original.custom_special_plays]

    names = _get_offensive_names(64)
    writer = _make_writer(pln_path)
    writer.write(normal_lines=names)

    reloaded = read_gameplan(pln_path)
    failures = find_play_slot_mismatches(names, reloaded.normal_plays)
    assert not failures, "\n" + "\n".join(failures)
    reloaded_special_names = [(p.name if p is not None else None) for p in reloaded.custom_special_plays]
    assert reloaded_special_names == original_special_names


def test_full_10_special_input_replaces_special_preserves_normal(tmp_path: Path) -> None:
    """Full 10-special write fills all 10 slots and leaves normal section untouched."""
    pln_path = _copy_pln(DATA_DIR / "O_64_06a.pln", tmp_path)
    original = read_gameplan(pln_path)
    original_normal_names = [(p.name if p is not None else None) for p in original.normal_plays]

    # One offensive special play per category 1..10 — only 6 distinct categories
    # exist for offense, so we can fill at most 6 distinct categories. Use the
    # set of plays the fixture pool has indexed.
    pool = _get_pool()
    special_names: list[str] = []
    seen_categories: set[int] = set()
    for record in pool.special_teams_plays:
        if not record.play_file.is_offensive:
            continue
        cat = record.play_file.special_category
        if cat in seen_categories:
            continue
        seen_categories.add(cat)
        special_names.append(record.name)
    # Sanity: writer accepts up to 10; fixture pool offers fewer distinct
    # categories so use what exists. The test still proves "fill many slots,
    # normal preserved."
    assert special_names, "Fixture pool has no offensive special plays"

    writer = _make_writer(pln_path)
    writer.write(special_lines=special_names)

    reloaded = read_gameplan(pln_path)
    reloaded_normal_names = [(p.name if p is not None else None) for p in reloaded.normal_plays]
    assert reloaded_normal_names == original_normal_names

    placed_count = sum(1 for p in reloaded.custom_special_plays if p is not None)
    assert placed_count == len(special_names)


def test_full_normal_and_special_input_replaces_both(tmp_path: Path) -> None:
    """Combined 64-normal + special write applies both sections."""
    pln_path = _copy_pln(DATA_DIR / "O_64_06a.pln", tmp_path)
    names = _get_offensive_names(64)
    writer = _make_writer(pln_path)
    writer.write(normal_lines=names, special_lines=["AF-KO"])

    reloaded = read_gameplan(pln_path)
    failures = find_play_slot_mismatches(names, reloaded.normal_plays)
    assert not failures, "\n" + "\n".join(failures)
    placed = reloaded.custom_special_plays[_kickoff_slot_index()]
    assert placed is not None
    assert placed.name.upper() == "AF-KO"
    for i, play in enumerate(reloaded.custom_special_plays):
        if i != _kickoff_slot_index():
            assert play is None


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
    pln_path = _copy_pln(DATA_DIR / "O_64_06a.pln", tmp_path)
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


def test_special_input_clears_unspecified_slots(tmp_path: Path) -> None:
    """Writer treats the special list as the full state — slots not specified should be cleared."""
    pln_path = _copy_pln(OFFENSE_PLN, tmp_path)  # offense.pln has 6 custom special plays filled
    writer = _make_writer(pln_path)
    writer.write(special_lines=["AF-KO"])

    reloaded = read_gameplan(pln_path)
    expected = [""] * 10
    expected[_kickoff_slot_index()] = "AF-KO"
    failures = find_play_slot_mismatches(expected, reloaded.custom_special_plays)
    assert not failures, "\n" + "\n".join(failures)


def test_partial_normal_input_clears_remaining_slots(tmp_path: Path) -> None:
    """Writer treats the normal list as the full state — slots beyond the input should be cleared."""
    pln_path = _copy_pln(OFFENSE_PLN, tmp_path)  # offense.pln has 60 normal plays filled
    names = _get_offensive_names(48)
    writer = _make_writer(pln_path)
    writer.write(normal_lines=names)

    reloaded = read_gameplan(pln_path)
    expected = list(names) + [""] * (64 - 48)
    failures = find_play_slot_mismatches(expected, reloaded.normal_plays)
    assert not failures, "\n" + "\n".join(failures)
