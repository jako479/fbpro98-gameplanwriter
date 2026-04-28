from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from conftest import OFFENSE_PLN, PLAYPOOL_DIR

from fbpro98_gameplan import read_gameplan
from fbpro98_gameplanwriter.cli import main, parse_args
from fbpro98_gameplanwriter.config import load_config
from fbpro98_gameplanwriter.gameplan_writer import GamePlanWriter


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


def test_from_config_builds_writer(tmp_path: Path) -> None:
    config_path = tmp_path / "test.ini"
    config_path.write_text(f"[Settings]\nPlayPath={PLAYPOOL_DIR}\n", encoding="utf-8")
    config = load_config(config_path=config_path)
    writer = GamePlanWriter.from_config(config, OFFENSE_PLN)
    assert writer.gameplan_path == OFFENSE_PLN
    assert writer.play_pool is not None


def test_main_writes_gameplan(tmp_path: Path) -> None:
    pln_path = tmp_path / "offense.pln"
    shutil.copy2(OFFENSE_PLN, pln_path)

    plays_txt = tmp_path / "plays.txt"
    plays_txt.write_text("OR45RL01\n", encoding="utf-8")

    rc = main([str(pln_path), str(plays_txt), "--play-path", str(PLAYPOOL_DIR)])
    assert rc == 0

    reloaded = read_gameplan(pln_path)
    assert reloaded.normal_plays[0] is not None
    assert reloaded.normal_plays[0].name == "OR45RL01"
    assert all(p is None for p in reloaded.normal_plays[1:])
