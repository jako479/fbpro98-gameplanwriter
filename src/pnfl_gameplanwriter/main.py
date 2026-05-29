from __future__ import annotations

import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TextIO

from fbpro98_gameplan import GamePlan

from pnfl_gameplanwriter.config import load_config
from pnfl_gameplanwriter.gameplan_writer import GamePlanWriter

STDIN_TOKEN = "-"
NORMAL_COUNT = GamePlan.NUMBER_NORMAL_PLAYS
SPECIAL_COUNT = GamePlan.NUMBER_SPECIAL_CATEGORIES
SHARED_COUNT = NORMAL_COUNT + SPECIAL_COUNT


@contextmanager
def open_input(source: str) -> Iterator[TextIO]:
    """Yield a readable text stream for ``source``.

    A source of '-' yields ``sys.stdin`` and never closes it. Any other value
    is treated as a filesystem path opened for reading in UTF-8.
    """
    if source == STDIN_TOKEN:
        yield sys.stdin
        return
    with open(source, encoding="utf-8") as f:
        yield f


def update_gameplan(
    *,
    gameplan_path: str | Path,
    normal_source: str | None,
    special_source: str | None,
    config_path: Path | None = None,
    play_path_override: str | None = None,
) -> None:
    """Apply the supplied normal/special play lists to the gameplan and persist it.

    A ``None`` source leaves that section untouched in the gameplan.
    """
    config = load_config(path=config_path, play_path=play_path_override)
    normal_lines, special_lines = _load_sections(normal_source, special_source)
    writer = GamePlanWriter.from_config(config, gameplan_path)
    writer.write(normal_lines=normal_lines, special_lines=special_lines)


def _read_source(source: str) -> str:
    with open_input(source) as f:
        return f.read()


def _load_sections(
    normal_source: str | None,
    special_source: str | None,
) -> tuple[list[str] | None, list[str] | None]:
    """Resolve the normal and special line lists from the supplied sources.

    When both flags share the same source (path or ``-``), the source is read
    once and split positionally: lines 0-63 → normal section, lines 64-73 →
    special section. Requires exactly 74 lines.

    When sources differ, each is read independently as a flat line list:
    ``--normal-plays`` accepts up to 64 lines, ``--special-plays`` up to 10.
    Over-max in either mode raises ValueError.
    """
    same_source = normal_source is not None and special_source is not None and normal_source == special_source
    if same_source:
        assert normal_source is not None
        lines = _read_source(normal_source).splitlines()
        if len(lines) != SHARED_COUNT:
            raise ValueError(
                f"Shared source must have exactly {SHARED_COUNT} lines "
                f"({NORMAL_COUNT} normal + {SPECIAL_COUNT} special), got {len(lines)}"
            )
        return lines[:NORMAL_COUNT], lines[NORMAL_COUNT:]

    normal_lines: list[str] | None = None
    if normal_source is not None:
        normal_lines = _read_source(normal_source).splitlines()
        if len(normal_lines) > NORMAL_COUNT:
            raise ValueError(f"--normal-plays source has {len(normal_lines)} lines, max is {NORMAL_COUNT}")

    special_lines: list[str] | None = None
    if special_source is not None:
        special_lines = _read_source(special_source).splitlines()
        if len(special_lines) > SPECIAL_COUNT:
            raise ValueError(f"--special-plays source has {len(special_lines)} lines, max is {SPECIAL_COUNT}")

    return normal_lines, special_lines
