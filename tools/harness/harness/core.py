"""Shared path, manifest and workspace helpers."""
from __future__ import annotations

import fnmatch
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
import tomllib

IGNORED = {".git", ".runtime", ".cache", ".venv", ".worktrees", "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache", "dist", "build", ".svelte-kit"}


def strict_json(text: str):
    def unique(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise ValueError("duplicate JSON key")
            obj[key] = value
        return obj
    def invalid_constant(_):
        raise ValueError("non-finite JSON")
    def finite_float(raw):
        value = float(raw)
        if not math.isfinite(value):
            raise ValueError("non-finite JSON")
        return value
    try:
        value = json.loads(text, object_pairs_hook=unique, parse_constant=invalid_constant, parse_float=finite_float)
    except RecursionError as exc:
        raise ValueError("JSON nesting exceeds parser limit") from exc
    # Bound depth independently of the interpreter's JSON implementation.
    frames = [iter((value,))]
    while frames:
        try:
            item = next(frames[-1])
        except StopIteration:
            frames.pop()
            continue
        if isinstance(item, (dict, list)):
            if len(frames) > 64:
                raise ValueError("JSON nesting exceeds 64 containers")
            frames.append(iter(item.values() if isinstance(item, dict) else item))
    return value


def inside(root: Path, relative: str) -> Path:
    if Path(relative).is_absolute():
        raise ValueError("repository paths must be relative")
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"repository path escapes root: {relative}")
    return path


def canonical_relative(root: Path, relative: str) -> str:
    """Resolve spelling aliases, including case/Unicode aliases on macOS."""
    resolved = inside(root, relative)
    cursor = root.resolve()
    parts = resolved.relative_to(cursor).parts
    for part in parts:
        if cursor.is_dir():
            names = {p.name for p in cursor.iterdir()}
            if part not in names and (cursor / part).exists():
                alias = cursor / part
                part = next((name for name in sorted(names) if (cursor / name).samefile(alias)), part)
        cursor = cursor / part
    return cursor.relative_to(root.resolve()).as_posix()


def runtime_path(root: Path, relative: str) -> Path:
    """Runtime output may not be redirected through repository symlinks."""
    if not relative.startswith('.runtime/'):
        raise ValueError('runtime output requires .runtime/')
    path = inside(root, relative)
    cursor = root.resolve()
    for part in Path(relative).parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError('runtime output symlinks are unsupported')
    if canonical_relative(root, relative) != relative:
        raise ValueError('runtime output needs its canonical repository path')
    return path


def matches(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, p) for p in patterns)


def _captured_inputs(root: Path) -> set[str]:
    path = runtime_path(root, '.runtime/source-inputs.json')
    if not path.exists():
        return set()
    if not path.is_file():
        raise ValueError('invalid captured source inventory')
    with path.open('rb') as stream:
        raw = stream.read(16 * 1024 * 1024 + 1)
    if len(raw) > 16 * 1024 * 1024:
        raise ValueError('captured source inventory exceeds limit')
    values = strict_json(raw.decode('utf-8'))
    if not isinstance(values, list) or not all(isinstance(p, str) and p for p in values):
        raise ValueError('invalid captured source inventory')
    return set(values)


def files(root: Path):
    def unreadable(error):
        raise error
    seen = set()
    for parent, dirs, names in os.walk(root, followlinks=False, onerror=unreadable):
        relative_parent = Path(parent).relative_to(root)
        in_project_docs = relative_parent.parts and relative_parent.parts[0] == 'docs'
        dirs[:] = sorted(d for d in dirs if d not in IGNORED or (in_project_docs and d in {'build', 'dist'}))
        if any((Path(parent) / d).is_symlink() for d in dirs):
            raise ValueError("source directory symlinks need explicit verification support")
        for name in sorted(names):
            path = Path(parent) / name
            if path.is_symlink():
                raise ValueError("source file symlinks need explicit verification support")
            if not path.is_file():
                raise ValueError('source inputs must be regular files')
            if not name.endswith((".pyc", ".pyo")):
                seen.add(path.relative_to(root).as_posix())
                yield path
    # Explicitly tracked sources override conventional artifact exclusions.
    # Otherwise a tracked backend/build/policy.py could bypass provenance.
    top = git(root, 'rev-parse', '--show-toplevel')
    if top.returncode == 0 and Path(os.fsdecode(top.stdout).strip()).resolve() == root.resolve():
        tracked = git(root, 'ls-files', '--cached', '-z')
        if tracked.returncode:
            raise ValueError('cannot enumerate tracked verification inputs')
        additional = {os.fsdecode(p) for p in tracked.stdout.split(b'\0') if p}
    else:
        # Captured archives retain the original explicit source inventory.
        additional = _captured_inputs(root)
    if additional:
        for relative in sorted(additional - seen):
            if any(p in {'.git', '.runtime', '.worktrees'} for p in Path(relative).parts):
                raise ValueError('tracked runtime outputs cannot be verification inputs')
            inside(root, relative)
            path = root / relative
            cursor = root / relative
            while cursor != root:
                if cursor.is_symlink():
                    raise ValueError('tracked source symlinks are unsupported')
                cursor = cursor.parent
            if not path.exists():
                continue
            if not path.is_file():
                raise ValueError('tracked inputs must be regular files; submodules need explicit support')
            yield path


def validate_checks(root: Path, checks: list[dict]) -> None:
    """Validate both harness and project checks using the same contract."""
    if not isinstance(checks, list):
        raise ValueError("checks must be an array of tables")
    seen = set()
    for check in checks:
        if not isinstance(check, dict):
            raise ValueError("check must be a table")
        allowed = {"id", "command", "cwd", "paths", "cacheable", "always", "covers_behavior",
                   "timeout", "max_output_bytes", "allow_flaky", "tier", "run_at", "test_summary"}
        if set(check) - allowed:
            raise ValueError("unknown check fields: " + ", ".join(sorted(set(check) - allowed)))
        name = check.get("id", "")
        if not isinstance(name, str) or not name or not all(c.isalnum() or c in "-_" for c in name) or name in seen:
            raise ValueError("check IDs must be unique simple names")
        seen.add(name)
        command = check.get("command")
        if not isinstance(command, list) or not command or not all(isinstance(x, str) and x for x in command):
            raise ValueError(f"invalid command: {name}")
        validate_patterns(check.get("paths"), f"path coverage: {name}")
        if not isinstance(check.get("cwd", "."), str):
            raise ValueError(f"invalid working directory: {name}")
        inside(root, check.get("cwd", "."))
        for field in ("cacheable", "always", "covers_behavior"):
            if not isinstance(check.get(field, False), bool):
                raise ValueError(f"invalid {field} setting: {name}")
        timeout = check.get("timeout", 120)
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0 < timeout <= 3600:
            raise ValueError(f"invalid timeout: {name}")
        limit = check.get("max_output_bytes", 4 * 1024 * 1024)
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 64 * 1024 * 1024:
            raise ValueError(f"invalid max_output_bytes: {name}")
        if not isinstance(check.get("allow_flaky", False), bool):
            raise ValueError(f"invalid allow_flaky: {name}")
        if check.get("tier", "change") not in ("change", "full"):
            raise ValueError(f"invalid check tier: {name}")
        if 'run_at' in check and (not isinstance(check['run_at'], list) or not check['run_at']
                or any(stage not in ('edit', 'feature', 'integration', 'final') for stage in check['run_at'])):
            raise ValueError(f"invalid check run_at: {name}")
        if check.get("test_summary") not in (None, "unittest", "junit"):
            raise ValueError(f"unsupported test summary parser: {name}")
        if check.get("test_summary") == "junit" and not any("{report}" in arg for arg in command):
            raise ValueError(f"JUnit check must write a fresh {{report}}: {name}")


def validate_patterns(patterns, label: str) -> None:
    if not isinstance(patterns, list) or not patterns or not all(
        isinstance(p, str) and p and not p.startswith('/') and '\\' not in p and '\0' not in p
        and not any(part in {'', '.', '..'} for part in p.split('/')) for p in patterns
    ):
        raise ValueError(f"invalid {label}")


def manifest(root: Path, workflow: str | None = None) -> dict:
    with (root / "tools/harness/harness.toml").open("rb") as stream:
        data = tomllib.load(stream)
    if data.get("version") != 1:
        raise ValueError("unsupported tools/harness/harness.toml version")
    validate_checks(root, data.get("checks"))
    if not data["checks"]:
        raise ValueError("no checks registered")
    if not isinstance(data.get("coverage", {}), dict):
        raise ValueError("coverage must be a table")
    docs = data.get("coverage", {}).get("documentation", [])
    if not isinstance(docs, list) or not all(isinstance(p, str) for p in docs):
        raise ValueError("invalid documentation coverage")
    from .workflows import load, selected_workflow, validate_impacts
    selected = selected_workflow(data, workflow)
    if selected:
        selected = canonical_relative(root, selected)
        project = load(root, selected)
        data["workflow"] = selected
        data["workflow_state"] = project["state"]
        data["security"] = project.get("security")
        data["security_review"] = project["security_review"]
        data["checks"].extend(project.get("checks", []))
        data["impacts"] = [*data.get("impacts", []), *project.get("impacts", [])]
        # The profile itself is executable configuration and must rerun its checks.
        for check in data["checks"]:
            check["paths"] = [*check["paths"], selected]
        validate_checks(root, data["checks"])
    validate_impacts(data.get("impacts", []), data["checks"])
    return data


def git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, check=False)


def source_paths(root: Path) -> list[str]:
    top = git(root, "rev-parse", "--show-toplevel")
    if top.returncode == 0 and Path(os.fsdecode(top.stdout).strip()).resolve() == root.resolve():
        result = git(root, "ls-files", "--cached", "--others", "--exclude-standard", "-z")
        if result.returncode:
            raise ValueError("cannot list repository sources")
        candidates = {os.fsdecode(p) for p in result.stdout.split(b"\0") if p}
        inputs = {p.relative_to(root).as_posix() for p in files(root)}
        return sorted(candidates & inputs)
    # A clean source archive has no .git metadata. Do not select machine-local
    # environment files, though fingerprints still consider env.
    declared = _captured_inputs(root)
    return [p.relative_to(root).as_posix() for p in files(root)
            if p.relative_to(root).as_posix() in declared or p.name == '.env.example'
            or (not p.name.startswith(".env") and p.name not in {"config.local.toml", "settings.local.json"})]


def changed_paths(root: Path, staged: bool = False) -> list[str]:
    args = ("diff", "--cached", "--name-only", "-z") if staged else ("diff", "--name-only", "-z", "HEAD")
    result = git(root, *args)
    # A newly initialized repository has no HEAD.
    if result.returncode and not staged:
        result = git(root, "diff", "--name-only", "-z")
    if result.returncode:
        raise ValueError("cannot inspect Git changes; use --paths or --full in a source archive")
    paths = set(os.fsdecode(p) for p in result.stdout.split(b"\0") if p)
    if not staged:
        other = git(root, "ls-files", "--others", "--exclude-standard", "-z")
        if other.returncode:
            raise ValueError("cannot inspect untracked paths")
        paths.update(os.fsdecode(p) for p in other.stdout.split(b"\0") if p)
        staged_result = git(root, "diff", "--cached", "--name-only", "-z")
        if staged_result.returncode:
            raise ValueError("cannot inspect staged paths")
        paths.update(os.fsdecode(p) for p in staged_result.stdout.split(b"\0") if p)
    return sorted(paths)


def fingerprint(root: Path) -> str:
    digest = hashlib.sha256()
    # Conservative reuse: source, tests, ignored .env files, inherited environment,
    # interpreter and platform. Runtime outputs are excluded.
    for path in files(root):
        relative = path.relative_to(root).as_posix()
        content_hash = hashlib.sha256()
        with path.open('rb') as stream:
            while chunk := stream.read(1024 * 1024):
                content_hash.update(chunk)
        entry = [relative, path.stat().st_mode & 0o111, content_hash.hexdigest()]
        digest.update(json.dumps(entry, ensure_ascii=True).encode() + b'\0')
    for relative in ["tools/harness/browser/node_modules/.package-lock.json", "backend/.venv/pyvenv.cfg"]:
        path = root / relative
        if path.is_file():
            digest.update(relative.encode() + path.read_bytes())
    # Tool-call tracing is not an execution condition; retaining it would miss
    # the cache on every Codex shell call despite identical code/environment.
    env = {k: v for k, v in os.environ.items() if k not in {"_", "PWD", "OLDPWD", "SHLVL", "CODEX_TOOL_CALL_ID"}}
    digest.update(json.dumps(env, sort_keys=True).encode())
    digest.update(repr((sys.executable, sys.version, platform.platform(), str(root.resolve()))).encode())
    return digest.hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
