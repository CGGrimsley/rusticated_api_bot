# tests/conftest.py
import sys
from pathlib import Path

# Project root (the folder that contains `pyproject.toml`)
ROOT = Path(__file__).resolve().parents[1]

# Put project root on sys.path
sys.path.insert(0, str(ROOT))

# If you ever move to a `src/` layout, this will also handle it:
SRC = ROOT / "src"
if SRC.exists():
    sys.path.insert(0, str(SRC))
