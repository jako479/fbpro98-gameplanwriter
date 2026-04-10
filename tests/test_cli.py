from __future__ import annotations

from pathlib import Path

import pytest

from fbpro98_gameplanwriter.cli import parse_args
from fbpro98_gameplanwriter.config import load_config


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


def test_config_play_path_override(tmp_path: Path) -> None:
    config_path = tmp_path / "write-gameplan.ini"
    config_path.write_text("[Settings]\nPlayPath=C:\\from-config\n", encoding="utf-8")

    assert load_config(config_path=config_path).Settings.PlayPath == "C:\\from-config"
    assert load_config(config_path=config_path, play_path=r"D:\from-cli").Settings.PlayPath == r"D:\from-cli"


def test_config_falls_back_to_defaults(tmp_path: Path) -> None:
    nonexistent = tmp_path / "nonexistent.ini"
    c = load_config(config_path=nonexistent)
    assert c.Settings.PlayPath == r"C:\SIERRA\FbPro98\PNFL"
