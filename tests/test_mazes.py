from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

"""Deprecated aggregate file kept for compatibility.

Real tests are now split by concern:
- test_core_maze.py
- test_generation.py
- test_layout.py
- test_localization.py
- test_pdf.py
"""
