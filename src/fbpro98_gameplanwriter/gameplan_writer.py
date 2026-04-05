from __future__ import annotations

import logging
from os import PathLike
from pathlib import Path

from fbpro98_gameplan import GamePlan, NormalPlayEntry, read_gameplan, write_normal_plays
from pnfl_playpool import (
    DefensivePlayRecord,
    OffensivePlayRecord,
    PlayPool,
    SpecialTeamsPlayRecord,
)

from .config import get_config

logger = logging.getLogger(__name__)

StrPath = str | PathLike[str]

MAX_NORMAL_PLAYS = 64
SLOTS_PER_ROW = 4


def _slot_label(slot: int) -> str:
    row = slot // SLOTS_PER_ROW + 1
    col = slot % SLOTS_PER_ROW + 1
    return f"{row}-{col}"


class GamePlanWriter:
    def __init__(
        self,
        play_pool: PlayPool,
        gameplan_path: StrPath,
    ) -> None:
        self.play_pool = play_pool
        self.gameplan_path = Path(gameplan_path)

    @classmethod
    def from_config(
        cls, gameplan_path: StrPath,
    ) -> GamePlanWriter:
        """Convenience factory — builds the play pool from config.

        This is not dependency injection itself; it's the factory that does
        the building so the constructor doesn't have to. Production code
        calls this; test code calls __init__ directly with a pre-built pool.
        """
        config = get_config()
        play_pool = PlayPool.from_directory(config.Settings.PlayPath)
        return cls(play_pool, gameplan_path)

    def write_from_play_list(self, plays_path: StrPath) -> None:
        gameplan = read_gameplan(self.gameplan_path)
        lines = Path(plays_path).read_text(encoding="utf-8").splitlines()
        lines = lines[:MAX_NORMAL_PLAYS]
        seen: dict[str, int] = {}
        entries: list[NormalPlayEntry | None] = []
        for slot, line in enumerate(lines):
            entry, name = self._resolve_line(slot, line, gameplan, seen)
            entries.append(entry)
            if name:
                seen[name] = slot
        write_normal_plays(self.gameplan_path, entries)
        play_count = sum(1 for e in entries if e is not None)
        logger.info("Wrote %d normal plays to '%s'", play_count, self.gameplan_path)

    def _resolve_line(
        self,
        slot: int,
        line: str,
        gameplan: GamePlan,
        seen: dict[str, int],
    ) -> tuple[NormalPlayEntry | None, str]:
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
        relative_path = record.file_path.relative_to(self.play_pool.root_dir)
        filename = str(relative_path).replace("/", "\\")
        return NormalPlayEntry(
            filename=f"PNFL\\{filename}",
            play_category=record.play_category,
            special_category=record.special_category,
            user_category=record.user_category,
        ), upper_name
