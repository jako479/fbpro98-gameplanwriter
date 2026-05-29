from __future__ import annotations

import configparser
from dataclasses import dataclass
from pathlib import Path

CONFIG_CANDIDATES = [
    Path.cwd() / "write-gameplan.dev.ini",
    Path.cwd() / "write-gameplan.ini",
    Path.cwd() / "config" / "write-gameplan.dev.ini",
    Path.cwd() / "config" / "write-gameplan.ini",
]

DEFAULT_PLAY_PATH = r"C:\SIERRA\FbPro98\PNFL"


@dataclass(frozen=True)
class Config:
    play_path: str = DEFAULT_PLAY_PATH


def load_config(
    path: Path | None = None,
    *,
    play_path: str | None = None,
) -> Config:
    cp = _read_config(path or find_config_path())
    return Config(
        play_path=play_path or cp.get("Settings", "PlayPath", fallback=DEFAULT_PLAY_PATH),
    )


def find_config_path() -> Path:
    return next(
        (c for c in CONFIG_CANDIDATES if c.is_file()),
        CONFIG_CANDIDATES[0],
    )


def _read_config(path: Path) -> configparser.ConfigParser:
    cp = configparser.ConfigParser()
    cp.read(path, encoding="utf-8")
    return cp
