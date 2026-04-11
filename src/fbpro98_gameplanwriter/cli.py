from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence
from pathlib import Path

from .config import load_config
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
        prog="pnfl write-gameplan",
        description="Update a gameplan (.pln) from a list of plays.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Play list file format:\n"
            "  - One play name per line.\n"
            "  - Blank lines produce empty slots in the gameplan.\n"
            "  - Play names are case-insensitive.\n"
            "  - Maximum 64 normal plays per gameplan; extra lines are ignored.\n"
            "  - Fewer than 64 lines: remaining slots are emptied.\n"
            "  - Unknown play names are skipped with a warning.\n"
            "  - Defensive plays in an offensive gameplan (and vice versa) are\n"
            "    skipped with a warning.\n"
            "  - Special-teams and clock plays in the existing gameplan are\n"
            "    preserved untouched.\n"
            "\n"
            "Example play list:\n"
            "  OR45RL01\n"
            "  OR10RLRG\n"
            "\n"
            "  SF35Hevy\n"
            "  OR36RL01\n"
            "\n"
            "(The blank third line above leaves slot 3 empty.)"
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

    config = load_config(
        config_path=args.config,
        play_path=args.play_path,
    )

    writer = GamePlanWriter.from_config(config, args.gameplan)
    writer.write_from_play_list(args.plays)
    return 0
