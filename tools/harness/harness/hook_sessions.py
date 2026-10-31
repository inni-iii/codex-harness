"""Explicit task bindings and private per-session lifecycle state."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
import re

from .core import runtime_path
from .provenance import atomic, load, now
from .evidence import task_file


def session_key(session):
    if not isinstance(session, str) or not session or len(session) > 500:
        raise ValueError("hook session ID is missing or exceeds its limit")
    return hashlib.sha256(session.encode()).hexdigest()[:24]


def selected_key(explicit=None):
    if explicit is not None:
        if not isinstance(explicit, str) or not re.fullmatch(r"[a-f0-9]{24}", explicit):
            raise ValueError("--session-key needs the 24-character key shown by SessionStart")
        return explicit
    return session_key(os.environ.get("CODEX_THREAD_ID"))


def state_path(root, key):
    selected_key(key)
    return runtime_path(root, f".runtime/hook-sessions/{key}.json")


def read(root, key):
    path = state_path(root, key)
    if not path.exists():
        return {"version": 1, "task": None}
    value = load(path, 1024 * 1024)
    if not isinstance(value, dict) or value.get("version") != 1:
        raise ValueError("invalid hook session state")
    task = value.get("task")
    if task is not None and (not isinstance(task, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", task)):
        raise ValueError("invalid hook task binding")
    return value


def save(root, key, state):
    encoded = json.dumps(state, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if len(encoded.replace("\n", os.linesep).encode()) > 1024 * 1024:
        raise ValueError("hook state exceeds size limit")
    atomic(state_path(root, key), state)


@contextmanager
def lock(root, key):
    path = runtime_path(root, f".runtime/hook-sessions/{selected_key(key)}.lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        yield False
        return
    try:
        os.close(fd)
        yield True
    finally:
        path.unlink(missing_ok=True)


def bind(root, slug, key=None):
    root = root.resolve()
    key = selected_key(key)
    data = load(task_file(root, slug), 128000)
    if not isinstance(data, dict) or data.get("status") not in {"planned", "in_progress", "needs_revision", "blocked"}:
        raise ValueError("bind an existing open task")
    with lock(root, key) as acquired:
        if not acquired:
            raise ValueError("hook state is busy; retry after the current callback")
        state = read(root, key)
        state.update(task=slug, bound_at=now())
        state.pop("stop_notice", None)
        save(root, key, state)
    return {"status": "passed", "session_key": key, "task": slug,
            "note": "Only this task is monitored. Binding does not approve or complete it."}


def clear(root, key=None):
    key = selected_key(key)
    with lock(root, key) as acquired:
        if not acquired:
            raise ValueError("hook state is busy")
        state = read(root, key)
        state.update(task=None)
        state.pop("stop_notice", None)
        save(root, key, state)
    return {"status": "passed", "session_key": key, "task": None}


def status(root, key=None):
    key = selected_key(key)
    state = read(root, key)
    validation = state.get("validation", {})
    return {"status": "passed", "session_key": key, "task": state.get("task"),
            "last_static_check": {k: validation[k] for k in ("status", "checks", "at") if k in validation}}
