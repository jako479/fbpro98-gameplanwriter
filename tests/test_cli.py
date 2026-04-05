from __future__ import annotations

from pathlib import Path

import pytest

from fbpro98_gameplanwriter.cli import parse_args
from fbpro98_gameplanwriter.config import get_config, set_config_path, set_play_path


def test_parse_args_requires_gameplan_and_plays() -> None:
    with pytest.raises(SystemExit):
        parse_args([])
    with pytest.raises(SystemExit):
        parse_args(["offense.pln"])


def test_parse_args_accepts_positional_args() -> None:
    args = parse_args(["offense.pln", "plays.txt"])
    assert args.gameplan == "offense.pln"
    assert args.plays == "plays.txt"
    assert args.play_path is None


def test_parse_args_accepts_pnfl_path_override() -> None:
    args = parse_args(["offense.pln", "plays.txt", "--play-path", r"E:\PNFL"])
    assert args.play_path == r"E:\PNFL"


def test_get_play_path_override_takes_precedence() -> None:
    set_play_path(r"D:\from-cli")
    result = get_config().Settings.PlayPath
    assert result == r"D:\from-cli"
    set_play_path(None)


def test_get_play_path_reads_config(tmp_path: Path) -> None:
    config_path = tmp_path / "gameplan_writer.ini"
    config_path.write_text("[Settings]\nPlayPath=C:\\from-config\n", encoding="utf-8")

    from fbpro98_gameplanwriter import config
    original_candidates = config.CONFIG_CANDIDATES
    config.CONFIG_CANDIDATES = [config_path]
    set_config_path(config_path)
    set_play_path(None)
    try:
        result = get_config().Settings.PlayPath
        assert result == r"C:\from-config"
    finally:
        config.CONFIG_CANDIDATES = original_candidates


def test_get_play_path_falls_back_to_default() -> None:
    from fbpro98_gameplanwriter import config
    original_candidates = config.CONFIG_CANDIDATES
    config.CONFIG_CANDIDATES = []
    set_play_path(None)
    set_config_path(Path("nonexistent.ini"))
    try:
        result = get_config().Settings.PlayPath
        assert result == r"C:\SIERRA\FbPro98\PNFL"
    finally:
        config.CONFIG_CANDIDATES = original_candidates
