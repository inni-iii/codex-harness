"""Local content-addressed evidence, with no credentials or source text in records."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import tempfile

from .core import canonical_relative, files, inside, strict_json


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise ValueError('content hashes require regular non-symlink files')
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def signature(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def load(path: Path, limit=16 * 1024 * 1024):
    if not path.is_file():
        raise ValueError('structured evidence must be a regular file')
    with path.open('rb') as stream:
        content = stream.read(limit + 1)
    if len(content) > limit:
        raise ValueError('structured evidence exceeds size limit')
    return strict_json(content.decode('utf-8'))


def atomic(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.harness-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def environment() -> dict:
    # Conditions are hashed, never exported. Database/service state is external.
    env = {k: v for k, v in os.environ.items()
           if k not in {'_', 'PWD', 'OLDPWD', 'SHLVL', 'CODEX_TOOL_CALL_ID'}}
    return {'python': sys.version, 'platform': platform.platform(),
            'python_executable': sys.executable, 'python_prefix': sys.prefix,
            'environment_sha256': signature(env)}


def snapshot(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): sha(p) for p in files(root)}


def executable_snapshot(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): p.stat().st_mode & 0o111 for p in files(root)}


def local_file(root: Path, relative: str) -> Path:
    path = inside(root, relative)
    # Reject aliases as well as escapes; evidence identifies one canonical file.
    if canonical_relative(root, relative) != relative or not path.is_file():
        raise ValueError('evidence needs an existing canonical repository-relative file')
    cursor = root
    for part in Path(relative).parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError('symlink evidence is unsupported')
    return path
