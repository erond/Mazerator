"""CLI launcher for the Streamlit web app."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


def main() -> int:
    app_path = Path(__file__).with_name("webapp.py")
    cmd = [sys.executable, "-m", "streamlit", "run", str(app_path)]
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
