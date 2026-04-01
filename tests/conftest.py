from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT.parent / "fbpro98-gameplan" / "src"))
sys.path.insert(0, str(PROJECT_ROOT.parent / "fbpro98-play" / "src"))
sys.path.insert(0, str(PROJECT_ROOT.parent / "pnfl-playpool" / "src"))
