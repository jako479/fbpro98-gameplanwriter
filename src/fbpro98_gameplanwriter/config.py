from __future__ import annotations

import configparser
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent.parent

DEFAULT_PNFL_PATH = r"C:\SIERRA\FbPro98\PNFL"

CONFIG_CANDIDATES = [
    PROJECT_DIR / "config" / "gameplan_writer.ini",
    SCRIPT_DIR / "gameplan_writer.ini",
]


def get_pnfl_path(
    override: str | Path | None = None,
    config_path: str | Path | None = None,
) -> Path:
    if override is not None:
        return Path(override).expanduser()
    parser = configparser.ConfigParser()
    if config_path is not None:
        parser.read(Path(config_path).expanduser().resolve(), encoding="utf-8")
    else:
        for candidate in CONFIG_CANDIDATES:
            if candidate.is_file():
                parser.read(candidate, encoding="utf-8")
                break
    return Path(parser.get("Settings", "PnflPath", fallback=DEFAULT_PNFL_PATH))
