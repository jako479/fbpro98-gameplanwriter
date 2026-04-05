from __future__ import annotations

import configparser
from dataclasses import dataclass
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent.parent

DEFAULT_PLAY_PATH = r"C:\SIERRA\FbPro98\PNFL"

CONFIG_CANDIDATES = [
    Path.cwd() / "gameplan_writer.ini",
    SCRIPT_DIR / "gameplan_writer.ini",
    PROJECT_DIR / "config" / "gameplan_writer.ini",
]

_config_path: Path | None = None
_config: AppConfig | None = None
_play_path_override: str | None = None


@dataclass
class Settings:
    Team: str = ""
    PlayPath: str = DEFAULT_PLAY_PATH
    CalculateTotalStats: bool = True
    CalculateCategoryStats: bool = False
    CalculateGroupedCategoryStats: bool = False


@dataclass
class AppConfig:
    Settings: Settings


def get_runtime_path(filename: str) -> Path:
    return SCRIPT_DIR / filename


def get_config_path() -> Path:
    global _config_path
    if _config_path is None:
        _config_path = next(
            (c for c in CONFIG_CANDIDATES if c.is_file()),
            CONFIG_CANDIDATES[0],
        )
    return _config_path


def set_config_path(config_path: str | Path) -> None:
    global _config_path, _config
    _config_path = Path(config_path).expanduser().resolve()
    _config = None


def set_play_path(play_path: str | None) -> None:
    global _play_path_override, _config
    _play_path_override = play_path
    _config = None


def get_config() -> AppConfig:
    global _config
    if _config is not None:
        return _config

    cp = configparser.ConfigParser()
    cp.read(get_config_path(), encoding="utf-8")

    settings = Settings(
        PlayPath=cp.get("Settings", "PlayPath", fallback=DEFAULT_PLAY_PATH),
    )

    if _play_path_override is not None:
        settings.PlayPath = _play_path_override

    _config = AppConfig(Settings=settings)
    return _config
