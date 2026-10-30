#!/usr/bin/env python3
"""Repository entrypoint; works without installing the Python package."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
