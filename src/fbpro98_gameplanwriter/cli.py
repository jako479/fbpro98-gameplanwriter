from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence

from .config import get_pnfl_path
from .gameplan_writer import GamePlanWriter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fbpro98-gameplanwriter",
        description="Update a .pln file from a list of plays.",
        epilog=(
            "The play list file should contain one play name per line. "
            "Empty lines produce empty slots. "
            "Maximum 64 normal plays per gameplan."
        ),
    )
    parser.add_argument("gameplan", help="Path to the .pln gameplan file to update")
    parser.add_argument(
        "plays",
        help="Path to a text file listing play names (one per line)",
    )
    parser.add_argument(
        "--config",
        help="Use this INI file instead of the default config lookup",
    )
    parser.add_argument(
        "--pnfl-path",
        help="Use this play pool path instead of Settings.PnflPath from config",
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
    pnfl_path = get_pnfl_path(config_path=args.config, override=args.pnfl_path)
    writer = GamePlanWriter(args.gameplan, pnfl_path)
    writer.write_from_play_list(args.plays)
    return 0
