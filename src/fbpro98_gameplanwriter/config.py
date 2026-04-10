from __future__ import annotations

import configparser
from dataclasses import dataclass
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = PACKAGE_DIR.parent.parent

DEFAULT_PLAY_PATH = r"C:\SIERRA\FbPro98\PNFL"

CONFIG_CANDIDATES = [
    Path.cwd() / "write-gameplan.dev.ini",
    Path.cwd() / "write-gameplan.ini",
    PROJECT_DIR / "config" / "write-gameplan.dev.ini",
    PROJECT_DIR / "config" / "write-gameplan.ini",
    PACKAGE_DIR / "write-gameplan.dev.ini",
    PACKAGE_DIR / "write-gameplan.ini",
]


@dataclass(frozen=True)
class Settings:
    PlayPath: str = DEFAULT_PLAY_PATH


@dataclass(frozen=True)
class AppConfig:
    Settings: Settings


def find_config_path() -> Path:
    return next(
        (c for c in CONFIG_CANDIDATES if c.is_file()),
        CONFIG_CANDIDATES[0],
    )


def load_config(
    config_path: Path | None = None,
    play_path: str | None = None,
) -> AppConfig:
    path = config_path or find_config_path()
    cp = configparser.ConfigParser()
    cp.read(path, encoding="utf-8")

    return AppConfig(
        Settings=Settings(
            PlayPath=play_path or cp.get("Settings", "PlayPath", fallback=DEFAULT_PLAY_PATH),
        ),
    )
