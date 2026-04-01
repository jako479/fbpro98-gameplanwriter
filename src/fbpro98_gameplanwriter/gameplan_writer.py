from __future__ import annotations

import logging
from os import PathLike
from pathlib import Path

from fbpro98_gameplan import Gameplan, NormalPlayEntry, read_gameplan, write_normal_plays
from pnfl_playpool import PlayPool, PlayRecord

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
        gameplan_path: StrPath,
        pnfl_path: StrPath,
    ) -> None:
        self.gameplan_path = Path(gameplan_path)
        self.pnfl_path = Path(pnfl_path)
        self._pool: PlayPool | None = None

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
        logger.info(
            "Wrote %d normal plays to '%s'", play_count, self.gameplan_path,
        )

    def _resolve_line(
        self, slot: int, line: str, gameplan: Gameplan, seen: dict[str, int],
    ) -> tuple[NormalPlayEntry | None, str]:
        name = line.strip()
        if not name:
            return None, ""
        upper_name = name.upper()
        if upper_name in seen:
            logger.warning(
                "Duplicate play '%s' at slot %s (line %d), already at slot %s (line %d), skipping",
                name,
                _slot_label(slot), slot + 1,
                _slot_label(seen[upper_name]), seen[upper_name] + 1,
            )
            return None, ""
        record, side = self._find_play(name)
        if record is None:
            logger.warning("Play not found in PNFL play pool, skipping: %s", name)
            return None, ""
        if side == "special":
            logger.warning(
                "Play '%s' is a special teams play, cannot add to normal slots, skipping", name,
            )
            return None, ""
        if gameplan.is_offense and side != "offense":
            logger.warning(
                "Play '%s' is a defensive play but gameplan is offensive, skipping", name,
            )
            return None, ""
        if gameplan.is_defense and side != "defense":
            logger.warning(
                "Play '%s' is an offensive play but gameplan is defensive, skipping", name,
            )
            return None, ""
        relative_path = record.file_path.relative_to(self.pnfl_path)
        filename = str(relative_path).replace("/", "\\")
        return NormalPlayEntry(
            filename=f"PNFL\\{filename}",
            play_category=record.play_category,
            special_category=record.play_file.special_category,
            user_category=record.user_category,
        ), upper_name

    def _find_play(self, name: str) -> tuple[PlayRecord | None, str]:
        pool = self._load_pool()
        upper_name = name.upper()
        for play in pool.offensive_plays:
            if play.name == upper_name:
                return play, "offense"
        for play in pool.defensive_plays:
            if play.name == upper_name:
                return play, "defense"
        for play in pool.special_teams_plays:
            if play.name == upper_name:
                return play, "special"
        return None, ""

    def _load_pool(self) -> PlayPool:
        if self._pool is None:
            self._pool = PlayPool.from_directory(self.pnfl_path)
        return self._pool
