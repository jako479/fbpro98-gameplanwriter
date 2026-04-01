from __future__ import annotations

from pathlib import Path

import pytest

from fbpro98_gameplanwriter.cli import parse_args
from fbpro98_gameplanwriter.config import get_pnfl_path


def test_parse_args_requires_gameplan_and_plays() -> None:
    with pytest.raises(SystemExit):
        parse_args([])
    with pytest.raises(SystemExit):
        parse_args(["offense.pln"])


def test_parse_args_accepts_positional_args() -> None:
    args = parse_args(["offense.pln", "plays.txt"])
    assert args.gameplan == "offense.pln"
    assert args.plays == "plays.txt"
    assert args.pnfl_path is None


def test_parse_args_accepts_pnfl_path_override() -> None:
    args = parse_args(["offense.pln", "plays.txt", "--pnfl-path", r"E:\PNFL"])
    assert args.pnfl_path == r"E:\PNFL"


def test_get_pnfl_path_override_takes_precedence() -> None:
    result = get_pnfl_path(r"D:\from-cli")
    assert result == Path(r"D:\from-cli")


def test_get_pnfl_path_reads_config(tmp_path: Path) -> None:
    config_path = tmp_path / "config" / "gameplan_writer.ini"
    config_path.parent.mkdir()
    config_path.write_text("[Settings]\nPnflPath=C:\\from-config\n", encoding="utf-8")

    from fbpro98_gameplanwriter import config
    original_candidates = config.CONFIG_CANDIDATES
    config.CONFIG_CANDIDATES = [config_path]
    try:
        result = get_pnfl_path(None)
        assert result == Path(r"C:\from-config")
    finally:
        config.CONFIG_CANDIDATES = original_candidates


def test_get_pnfl_path_falls_back_to_default() -> None:
    result = get_pnfl_path(None)
    assert result == Path(r"C:\SIERRA\FbPro98\PNFL")
