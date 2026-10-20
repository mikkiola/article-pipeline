"""Puts the repository root and the bare-import source directories on
sys.path, the way the other test directories of this repository do."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for sub in ("", "strategy_layer", "strategy_layer/adapters", "author"):
    sys.path.insert(0, str(ROOT / sub) if sub else str(ROOT))
