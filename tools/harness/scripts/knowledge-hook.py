#!/usr/bin/env python3
"""Repository-local Codex hook entrypoint; no external packages or model calls."""
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root / "tools/harness"))
from harness.knowledge_hooks import main

if __name__ == "__main__":
    raise SystemExit(main(root))
