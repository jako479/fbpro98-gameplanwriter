from __future__ import annotations

from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
DATA_DIR = TESTS_DIR / "data"
EXPECTED_DIR = DATA_DIR / "expected"
PLAYPOOL_DIR = DATA_DIR / "plays"
OFFENSE_PLN = DATA_DIR / "O_60_06.pln"
DEFENSE_PLN = DATA_DIR / "D_50_09.pln"


@pytest.fixture
def playpool_dir() -> Path:
    return PLAYPOOL_DIR


@pytest.fixture
def offense_pln() -> Path:
    return OFFENSE_PLN


@pytest.fixture
def defense_pln() -> Path:
    return DEFENSE_PLN
