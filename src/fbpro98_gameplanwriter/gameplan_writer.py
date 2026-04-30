"""Apply play-list updates to FbPro98 gameplan (.pln) files.

Resolves play names against the PNFL play pool, validates them against the
target gameplan's offense/defense type, and writes the updated normal and
custom-special slots back to disk.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from os import PathLike
from pathlib import Path

from fbpro98_gameplan import CustomPlay, GamePlan, read_gameplan, write_gameplan
from pnfl_playpool import (
    DefensivePlayRecord,
    OffensivePlayRecord,
    PlayPool,
    SpecialTeamsPlayRecord,
)

from fbpro98_gameplanwriter.config import Config

logger = logging.getLogger(__name__)

StrPath = str | PathLike[str]

MAX_NORMAL_PLAYS = 64
SLOTS_PER_ROW = 4
SPECIAL_CATEGORIES = 10

NORMAL_HEADER = "=== normal ==="
SPECIAL_HEADER = "=== special ==="


def _slot_label(slot: int) -> str:
    row = slot // SLOTS_PER_ROW + 1
    col = slot % SLOTS_PER_ROW + 1
    return f"{row}-{col}"


def parse_sections(text: str, *, default_section: str = "normal") -> dict[str, list[str]]:
    """Split a combined-format play list into normal and special line groups.

    Lines `=== Normal ===` and `=== Special ===` (case-insensitive, surrounding
    whitespace tolerated) act as section markers. Lines that appear before any
    marker fall into `default_section` ('normal' or 'special'). Marker lines
    themselves are dropped; all other lines (including blanks) are preserved in
    their section's list.
    """
    if default_section not in ("normal", "special"):
        raise ValueError(f"default_section must be 'normal' or 'special', got {default_section!r}")
    sections: dict[str, list[str]] = {"normal": [], "special": []}
    current = default_section
    for line in text.splitlines():
        marker = line.strip().lower()
        if marker == NORMAL_HEADER:
            current = "normal"
            continue
        if marker == SPECIAL_HEADER:
            current = "special"
            continue
        sections[current].append(line)
    return sections


def _build_custom_play(record: object, play_pool_root: Path) -> CustomPlay:
    """Construct the CustomPlay reference the .pln stores for a play pool record."""
    record_path: Path = record.file_path  # type: ignore[attr-defined]
    relative_path = record_path.relative_to(play_pool_root)
    filename = str(relative_path).replace("/", "\\")
    return CustomPlay(
        filename=f"PNFL\\{filename}",
        play_category=record.play_category,  # type: ignore[attr-defined]
        special_category=record.special_category,  # type: ignore[attr-defined]
        user_category=record.user_category,  # type: ignore[attr-defined]
    )


class GamePlanWriter:
    """Writes play lists into a .pln, resolving names via PlayPool and validating fit."""

    def __init__(
        self,
        play_pool: PlayPool,
        gameplan_path: StrPath,
    ) -> None:
        self.play_pool = play_pool
        self.gameplan_path = Path(gameplan_path)

    @classmethod
    def from_config(
        cls,
        config: Config,
        gameplan_path: StrPath,
    ) -> GamePlanWriter:
        play_pool = PlayPool.from_directory(config.play_path)
        return cls(play_pool, gameplan_path)

    def write(
        self,
        *,
        normal_lines: Sequence[str] | None = None,
        special_lines: Sequence[str] | None = None,
    ) -> None:
        """Apply the given play lists to the gameplan and persist it.

        A `None` section is left untouched in the existing gameplan; an empty
        list clears that section's slots.
        """
        gameplan = read_gameplan(self.gameplan_path)
        if normal_lines is not None:
            gameplan = self.apply_normal_plays(gameplan, normal_lines)
        if special_lines is not None:
            gameplan = self.apply_special_plays(gameplan, special_lines)
        write_gameplan(gameplan, self.gameplan_path)
        if normal_lines is not None:
            count = sum(1 for p in gameplan.normal_plays if p is not None)
            logger.info("Wrote %d normal plays to '%s'", count, self.gameplan_path)
        if special_lines is not None:
            count = sum(1 for p in gameplan.custom_special_plays if p is not None)
            logger.info("Wrote %d custom special plays to '%s'", count, self.gameplan_path)

    def apply_normal_plays(
        self,
        gameplan: GamePlan,
        lines: Sequence[str],
    ) -> GamePlan:
        """Place plays into the 64 normal slots in input order.

        Truncates `lines` to MAX_NORMAL_PLAYS (64); extras are silently dropped.
        Empty lines and duplicates leave their slot empty (with a warning for
        duplicates). Plays not in the pool, special-teams plays, and plays of
        the wrong offensive/defensive type for `gameplan` are skipped with a
        warning. Returns a new GamePlan; the input is not mutated.
        """
        truncated = list(lines)[:MAX_NORMAL_PLAYS]
        seen: dict[str, int] = {}
        entries: list[CustomPlay | None] = []
        for slot, line in enumerate(truncated):
            entry, name = self._resolve_normal_line(slot, line, gameplan, seen)
            entries.append(entry)
            if name:
                seen[name] = slot
        return gameplan.with_normal_plays(entries)

    def apply_special_plays(
        self,
        gameplan: GamePlan,
        lines: Sequence[str],
    ) -> GamePlan:
        """Place special plays into the 10 special-teams slots, keyed by `special_category`.

        Each play's `special_category` (1..10) determines its slot — input order
        only matters for tie-breaking when two lines target the same category
        (the first wins; subsequent are skipped with a warning). Empty lines,
        duplicates, plays not in the pool, plays of the wrong offensive/defensive
        type, and out-of-range categories are skipped with a warning. Returns a
        new GamePlan; the input is not mutated.
        """
        slots: list[CustomPlay | None] = [None] * SPECIAL_CATEGORIES
        seen_names: dict[str, int] = {}  # upper name -> special_category
        for line_index, line in enumerate(lines):
            name = line.strip()
            if not name:
                continue
            entry = self._resolve_special_line(line_index, name, gameplan, seen_names, slots)
            if entry is not None:
                cat = entry.special_category
                slots[cat - 1] = entry
                seen_names[name.upper()] = cat
        return gameplan.with_custom_special_plays(slots)

    def _resolve_normal_line(
        self,
        slot: int,
        line: str,
        gameplan: GamePlan,
        seen: dict[str, int],
    ) -> tuple[CustomPlay | None, str]:
        name = line.strip()
        if not name:
            return None, ""
        upper_name = name.upper()
        if upper_name in seen:
            logger.warning(
                "Duplicate play '%s' at slot %s (line %d), already at slot %s (line %d), skipping",
                name,
                _slot_label(slot),
                slot + 1,
                _slot_label(seen[upper_name]),
                seen[upper_name] + 1,
            )
            return None, ""
        record = self.play_pool.find_by_name(name)
        if record is None:
            logger.warning("Play not found in PNFL play pool, skipping: %s", name)
            return None, ""
        if isinstance(record, SpecialTeamsPlayRecord):
            logger.warning(
                "Play '%s' is a special teams play, cannot add to normal slots, skipping",
                name,
            )
            return None, ""
        if gameplan.is_offense and isinstance(record, DefensivePlayRecord):
            logger.warning(
                "Play '%s' is a defensive play but gameplan is offensive, skipping",
                name,
            )
            return None, ""
        if gameplan.is_defense and isinstance(record, OffensivePlayRecord):
            logger.warning(
                "Play '%s' is an offensive play but gameplan is defensive, skipping",
                name,
            )
            return None, ""
        return _build_custom_play(record, self.play_pool.root_dir), upper_name

    def _resolve_special_line(
        self,
        line_index: int,
        name: str,
        gameplan: GamePlan,
        seen_names: dict[str, int],
        slots: list[CustomPlay | None],
    ) -> CustomPlay | None:
        upper_name = name.upper()
        line_no = line_index + 1
        if upper_name in seen_names:
            logger.warning(
                "Duplicate special play '%s' at line %d, already used for special category %d, skipping",
                name,
                line_no,
                seen_names[upper_name],
            )
            return None
        record = self.play_pool.find_by_name(name)
        if record is None:
            logger.warning(
                "Special play not found in PNFL play pool at line %d, skipping: %s",
                line_no,
                name,
            )
            return None
        if not isinstance(record, SpecialTeamsPlayRecord):
            logger.warning(
                "Play '%s' at line %d is not a special teams play, skipping",
                name,
                line_no,
            )
            return None
        cat = record.special_category
        if cat < 1 or cat > SPECIAL_CATEGORIES:
            logger.warning(
                "Special play '%s' at line %d has out-of-range special_category=%d, skipping",
                name,
                line_no,
                cat,
            )
            return None
        if gameplan.is_offense and not record.play_file.is_offensive:
            logger.warning(
                "Play '%s' at line %d is a defensive special play but gameplan is offensive, skipping",
                name,
                line_no,
            )
            return None
        if gameplan.is_defense and not record.play_file.is_defensive:
            logger.warning(
                "Play '%s' at line %d is an offensive special play but gameplan is defensive, skipping",
                name,
                line_no,
            )
            return None
        if slots[cat - 1] is not None:
            logger.warning(
                "Special play '%s' at line %d targets special category %d, already filled by another play, skipping",
                name,
                line_no,
                cat,
            )
            return None
        return _build_custom_play(record, self.play_pool.root_dir)
