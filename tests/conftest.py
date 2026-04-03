from __future__ import annotations

from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
FIXTURES_DIR = TESTS_DIR / "fixtures"
PLAYPOOL_DIR = FIXTURES_DIR / "plays"
OFFENSE_DIR = FIXTURES_DIR / "offense"
DEFENSE_DIR = FIXTURES_DIR / "defense"
OFFENSE_PLN = OFFENSE_DIR / "offense.pln"
DEFENSE_PLN = DEFENSE_DIR / "defense.pln"


@pytest.fixture
def playpool_dir() -> Path:
    return PLAYPOOL_DIR


@pytest.fixture
def offense_pln() -> Path:
    return OFFENSE_PLN


@pytest.fixture
def defense_pln() -> Path:
    return DEFENSE_PLN
