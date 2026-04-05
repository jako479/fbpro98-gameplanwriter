from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence
from pathlib import Path

from .config import set_config_path, set_play_path
from .gameplan_writer import GamePlanWriter


def _valid_existing_file(param: str, expected_extensions: tuple[str, ...]) -> str:
    filepath = Path(param).expanduser()
    if filepath.suffix.lower() not in expected_extensions:
        extensions = ", ".join(expected_extensions)
        raise argparse.ArgumentTypeError(f"File must have one of these extensions: {extensions}")
    if not filepath.is_file():
        raise argparse.ArgumentTypeError(f"File not found: {filepath}")
    return str(filepath)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fbpro98-gameplanwriter",
        description="Update a gameplan (.pln) from a list of plays.",
        epilog=(
            "The play list file should contain one play name per line. "
            "Empty lines produce empty slots. "
            "Maximum 64 normal plays per gameplan."
        ),
    )
    parser.add_argument(
        "gameplan",
        help="Path to the .pln gameplan file to update",
    )
    parser.add_argument(
        "plays",
        help="Path to a text file listing play names (one per line)",
    )
    parser.add_argument(
        "--config",
        type=lambda v: _valid_existing_file(v, (".ini",)),
        help="Use this INI file instead of the default config lookup",
    )
    parser.add_argument(
        "--play-path",
        help="Path to PNFL play files directory (overrides config Settings.PlayPath)",
    )
    return parser


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = build_parser()
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    if args.config:
        set_config_path(args.config)
    set_play_path(args.play_path)

    writer = GamePlanWriter.from_config(args.gameplan)
    writer.write_from_play_list(args.plays)
    return 0
