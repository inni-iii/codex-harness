#!/usr/bin/env python3
"""Repo-local Codex UserPromptSubmit adapter."""
from pathlib import Path
from harness.routing.hooks import prompt_hook

if __name__ == "__main__":
    raise SystemExit(prompt_hook(Path(__file__).resolve().parents[2]))
