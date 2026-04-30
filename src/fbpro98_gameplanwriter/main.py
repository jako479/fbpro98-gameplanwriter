from __future__ import annotations

import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TextIO

from fbpro98_gameplanwriter.config import load_config
from fbpro98_gameplanwriter.gameplan_writer import GamePlanWriter, parse_sections

STDIN_TOKEN = "-"


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

    Stdin is consumed at most once: when both flags share a source (path or
    ``-``), the file or stream is read once and dispatched via section markers.
    """
    same_source = normal_source is not None and special_source is not None and normal_source == special_source
    if same_source:
        assert normal_source is not None
        sections = parse_sections(_read_source(normal_source), default_section="normal")
        return sections["normal"], sections["special"]

    normal_lines: list[str] | None = None
    if normal_source is not None:
        sections = parse_sections(_read_source(normal_source), default_section="normal")
        normal_lines = sections["normal"]

    special_lines: list[str] | None = None
    if special_source is not None:
        sections = parse_sections(_read_source(special_source), default_section="special")
        special_lines = sections["special"]

    return normal_lines, special_lines
