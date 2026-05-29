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

from fbpro98_gameplan import CustomPlay, GamePlan, write_gameplan
from pnfl_gameplan import PNFL_RULES, PnflGamePlan, PnflRules
from pnfl_playpool import (
    DefensivePlayRecord,
    OffensivePlayRecord,
    PlayPool,
    SpecialTeamsPlayRecord,
    read_play_pool,
)

from pnfl_gameplanwriter.config import Config

logger = logging.getLogger(__name__)

StrPath = str | PathLike[str]

MAX_NORMAL_PLAYS = 64
SLOTS_PER_ROW = 4


def _slot_label(slot: int) -> str:
    row = slot // SLOTS_PER_ROW + 1
    col = slot % SLOTS_PER_ROW + 1
    return f"{row}-{col}"


class InvalidPlayInputError(ValueError):
    """Raised by `GamePlanWriter` when input lines contain rule violations.

    Violations are collected across the full input pass so the user sees every
    problem in one error rather than fixing one at a time. The full per-line
    messages are available via the `violations` attribute.
    """

    def __init__(self, violations: list[str]) -> None:
        self.violations = list(violations)
        body = "\n  - ".join(self.violations)
        super().__init__(f"{len(self.violations)} invalid input line(s):\n  - {body}")


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
        *,
        rules: PnflRules = PNFL_RULES,
    ) -> None:
        self.play_pool = play_pool
        self.gameplan_path = Path(gameplan_path)
        self.rules = rules

    @classmethod
    def from_config(
        cls,
        config: Config,
        gameplan_path: StrPath,
        *,
        rules: PnflRules = PNFL_RULES,
    ) -> GamePlanWriter:
        play_path = Path(config.play_path)
        if not play_path.is_dir():
            raise FileNotFoundError(f"Play pool path does not exist or is not a directory: {config.play_path}")
        play_pool = read_play_pool(config.play_path)
        if not (play_pool.offensive_plays or play_pool.defensive_plays or play_pool.special_teams_plays):
            raise ValueError(f"Play pool at {config.play_path} contains no plays")
        return cls(play_pool, gameplan_path, rules=rules)

    def write(
        self,
        *,
        normal_lines: Sequence[str] | None = None,
        special_lines: Sequence[str] | None = None,
    ) -> None:
        """Apply the given play lists to the gameplan and persist it.

        A `None` section is left untouched in the existing gameplan; an empty
        list clears that section's slots.

        Loads the target via `PnflGamePlan.from_file` (binding the gameplan to
        the writer's PnflRules + PlayPool), modifies the underlying `GamePlan`,
        and persists with `write_gameplan`. PNFL-rule validation is not run
        automatically here — callers that want a validated save can do so via
        `PnflGamePlan.from_file(path, rules, pool).save(path)` after this
        method returns.
        """
        pnfl_gameplan = PnflGamePlan.from_file(str(self.gameplan_path), self.rules, self.play_pool)
        gameplan = pnfl_gameplan.gameplan
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
        Empty lines leave their slot empty. Duplicates, plays not in the pool,
        special-teams plays, and plays of the wrong offensive/defensive type
        are collected across the full input and raised as `InvalidPlayInputError`
        at the end of the pass. Returns a new GamePlan; the input is not
        mutated.
        """
        truncated = list(lines)[:MAX_NORMAL_PLAYS]
        seen: dict[str, int] = {}
        entries: list[CustomPlay | None] = []
        violations: list[str] = []
        for slot, line in enumerate(truncated):
            entry, name = self._resolve_normal_line(slot, line, gameplan, seen, violations)
            entries.append(entry)
            if name:
                seen[name] = slot
        if violations:
            raise InvalidPlayInputError(violations)
        return gameplan.with_normal_plays(entries)

    def apply_special_plays(
        self,
        gameplan: GamePlan,
        lines: Sequence[str],
    ) -> GamePlan:
        """Resolve special-play names from `lines` and place them in the gameplan.

        Empty lines are skipped. Duplicates, plays not in the pool, plays of
        the wrong offensive/defensive type, plays whose category collides with
        another already-placed play, and out-of-range categories are collected
        across the full input and raised as `InvalidPlayInputError` at the end
        of the pass. The model places each accepted play in its own
        `special_category` slot; categories not covered are cleared. Returns
        a new GamePlan; the input is not mutated.
        """
        seen_names: dict[str, int] = {}  # upper name -> special_category
        seen_categories: set[int] = set()
        plays: list[CustomPlay] = []
        violations: list[str] = []
        for line_index, line in enumerate(lines):
            name = line.strip()
            if not name:
                continue
            entry = self._resolve_special_line(line_index, name, gameplan, seen_names, seen_categories, violations)
            if entry is not None:
                plays.append(entry)
                seen_names[name.upper()] = entry.special_category
                seen_categories.add(entry.special_category)
        if violations:
            raise InvalidPlayInputError(violations)
        return gameplan.with_custom_special_plays(plays)

    def _resolve_normal_line(
        self,
        slot: int,
        line: str,
        gameplan: GamePlan,
        seen: dict[str, int],
        violations: list[str],
    ) -> tuple[CustomPlay | None, str]:
        name = line.strip()
        if not name:
            return None, ""
        upper_name = name.upper()
        line_no = slot + 1
        if upper_name in seen:
            violations.append(
                f"Duplicate play '{name}' at slot {_slot_label(slot)} (line {line_no}), "
                f"already at slot {_slot_label(seen[upper_name])} (line {seen[upper_name] + 1})"
            )
            return None, ""
        record = self.play_pool.find_by_name(name)
        if record is None:
            violations.append(f"Play not found in PNFL play pool at line {line_no}: {name}")
            return None, ""
        if isinstance(record, SpecialTeamsPlayRecord):
            violations.append(f"Play '{name}' at line {line_no} is a special teams play, cannot add to normal slots")
            return None, ""
        if gameplan.is_offense and isinstance(record, DefensivePlayRecord):
            violations.append(f"Play '{name}' at line {line_no} is a defensive play but gameplan is offensive")
            return None, ""
        if gameplan.is_defense and isinstance(record, OffensivePlayRecord):
            violations.append(f"Play '{name}' at line {line_no} is an offensive play but gameplan is defensive")
            return None, ""
        return _build_custom_play(record, self.play_pool.root_dir), upper_name

    def _resolve_special_line(
        self,
        line_index: int,
        name: str,
        gameplan: GamePlan,
        seen_names: dict[str, int],
        seen_categories: set[int],
        violations: list[str],
    ) -> CustomPlay | None:
        upper_name = name.upper()
        line_no = line_index + 1
        if upper_name in seen_names:
            violations.append(
                f"Duplicate special play '{name}' at line {line_no}, "
                f"already used for special category {seen_names[upper_name]}"
            )
            return None
        record = self.play_pool.find_by_name(name)
        if record is None:
            violations.append(f"Special play not found in PNFL play pool at line {line_no}: {name}")
            return None
        if not isinstance(record, SpecialTeamsPlayRecord):
            violations.append(f"Play '{name}' at line {line_no} is not a special teams play")
            return None
        cat = record.special_category
        if gameplan.is_offense and not record.play_file.is_offensive:
            violations.append(f"Play '{name}' at line {line_no} is a defensive special play but gameplan is offensive")
            return None
        if gameplan.is_defense and not record.play_file.is_defensive:
            violations.append(f"Play '{name}' at line {line_no} is an offensive special play but gameplan is defensive")
            return None
        if cat in seen_categories:
            violations.append(
                f"Special play '{name}' at line {line_no} targets special category {cat}, "
                f"already filled by another play"
            )
            return None
        return _build_custom_play(record, self.play_pool.root_dir)
