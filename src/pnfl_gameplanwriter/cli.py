from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence
from pathlib import Path

from pnfl_gameplanwriter.gameplan_writer import InvalidPlayInputError
from pnfl_gameplanwriter.main import update_gameplan

PROG = "pnfl write-gameplan"
logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG,
        description="Update a gameplan (.pln) from lists of normal and/or special teams plays.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Input sources:\n"
            "  --normal-plays SOURCE   Read up to 64 normal plays from SOURCE (file or '-' for stdin).\n"
            "  --special-plays SOURCE  Read up to 10 custom special teams plays from SOURCE.\n"
            "  At least one of --normal-plays or --special-plays is required.\n"
            "  A section that is not supplied is left untouched in the gameplan.\n"
            "  When both flags share the same source (path or '-'), the source must\n"
            "    contain exactly 74 lines: lines 0-63 -> normal, lines 64-73 -> special.\n"
            "\n"
            "Pipeline-friendly examples:\n"
            "  pnfl read-gameplan src.pln --normal-out - --special-out - | pnfl write-gameplan dest.pln --normal-plays - --special-plays -\n"  # noqa: E501
            "  pnfl read-gameplan src.pln --normal-out - | pnfl write-gameplan dest.pln --normal-plays -\n"
        ),
    )
    parser.add_argument(
        "gameplan_path",
        help="Path to the .pln gameplan file to update",
    )
    parser.add_argument(
        "--normal-plays",
        dest="normal_plays",
        metavar="SOURCE",
        help="File path (or '-' for stdin) containing the normal plays list",
    )
    parser.add_argument(
        "--special-plays",
        dest="special_plays",
        metavar="SOURCE",
        help="File path (or '-' for stdin) containing the custom special teams plays list",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Use this INI file instead of the default config lookup",
    )
    parser.add_argument(
        "--play-path",
        dest="play_path",
        help="Path to PNFL play files directory (overrides config [Settings] PlayPath)",
    )
    return parser


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.normal_plays is None and args.special_plays is None:
        parser.error("at least one of --normal-plays or --special-plays is required")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )
    try:
        update_gameplan(
            gameplan_path=args.gameplan_path,
            normal_source=args.normal_plays,
            special_source=args.special_plays,
            config_path=args.config,
            play_path_override=args.play_path,
        )
    except InvalidPlayInputError as error:
        for v in error.violations:
            logger.error("%s", v)
        logger.error("%d invalid input line(s) found. Gameplan NOT updated.", len(error.violations))
        return 1
    except OSError as error:
        logger.error("%s: %s", PROG, error)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
