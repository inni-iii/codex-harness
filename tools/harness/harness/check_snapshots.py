"""Verify one captured working tree while other sessions continue editing."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import uuid

from .core import fingerprint, inside, runtime_path, source_paths
from .checks import captured_run
from .provenance import atomic, sha, executable_snapshot


def run(root: Path, paths: list[str], *, full=False, workflow=None, checkpoint="feature") -> dict:
    root = root.resolve()
    if not paths and not full:
        return {"status": "no_checks", "snapshot": "working_tree", "product_accepted": False}
    directory = runtime_path(root, f".runtime/check-snapshots/{uuid.uuid4().hex}")
    directory.mkdir(parents=True, mode=0o700)
    source = directory / "source"
    source.mkdir(mode=0o700)
    before = fingerprint(root)
    captured = {}
    captured_executable = {}
    for relative in source_paths(root):
        path = inside(root, relative)
        if not path.exists():
            continue
        if not path.is_file():
            raise ValueError('snapshot sources must be regular files')
        cursor = root / relative
        while cursor != root:
            if cursor.is_symlink():
                raise ValueError("snapshot source symlinks are unsupported")
            cursor = cursor.parent
        data = path.read_bytes()
        target = source / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        executable = path.stat().st_mode & 0o111
        target.chmod(0o600 | executable)
        captured[relative] = hashlib.sha256(data).hexdigest()
        captured_executable[relative] = executable
    current = {relative: sha(inside(root, relative)) for relative in source_paths(root)
               if inside(root, relative).is_file()}
    after = fingerprint(root)
    current_executable = executable_snapshot(root)
    if (before != after or captured != current
            or captured_executable != {p: current_executable.get(p) for p in captured}):
        return {"status": "capture_changed", "snapshot": "working_tree", "product_accepted": False,
                "note": "Source changed during capture. No commands were run; capture again after coordinating that write."}
    entry = source / "tools/harness/run.py"
    if not entry.is_file():
        raise ValueError("snapshot must contain the repository harness entrypoint")
    atomic(source / '.runtime/source-inputs.json', sorted(captured))
    command = [sys.executable, str(entry), "check", "--report-dir", str(directory / "checks"),
               "--checkpoint", checkpoint, "--paths", *paths]
    if not paths:
        command = command[:-1]  # No empty --paths argument.
    if full:
        command.append("--full")
    if workflow:
        command.extend(["--project", workflow])
    # Execute the captured runner, not a new live version of its code.
    result = captured_run(command, source, directory / 'checks', timeout=3600)
    result.update(snapshot="working_tree", snapshot_origin=str(root),
                  snapshot_directory=str(source), captured_sources=captured,
                  live_source_changed=fingerprint(root) != before)
    result["completion_ready"] = result.get("status") == "passed"
    result["note"] = "Verified captured sources only. Private ignored files and installed dependency trees were not copied. Reconcile live changes before integration or completion."
    path = Path(result["report"]) if result.get("report") else directory / "report.json"
    atomic(path, result)
    result["report"] = str(path)
    return result
