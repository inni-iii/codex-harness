"""Project-local package selection and frozen installs; no global preferences."""
from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
import tomllib
import uuid

from .core import inside, runtime_path
from .provenance import load, local_file, sha
from .processes import execute

NODE_LOCKS = {"package-lock.json": "npm", "npm-shrinkwrap.json": "npm", "pnpm-lock.yaml": "pnpm",
              "yarn.lock": "yarn", "bun.lock": "bun", "bun.lockb": "bun"}


def _table(data, name):
    value = data.get(name, {})
    if not isinstance(value, dict):
        raise ValueError(f"manifest {name} must be a table")
    return value


def _directory(root, relative):
    path = inside(root, relative)
    cursor = root
    for part in Path(relative).parts:
        cursor /= part
        if cursor.is_symlink():
            raise ValueError("environment paths must not traverse symlinks")
    if not path.is_dir():
        raise ValueError("environment target must be an existing project directory")
    return path


def inspect(root, relative="."):
    root = root.resolve()
    directory = _directory(root, relative)
    groups, problems = [], []
    package = directory / "package.json"
    if package.exists():
        data = load(local_file(root, package.relative_to(root).as_posix()), 2 * 1024 * 1024)
        if not isinstance(data, dict):
            raise ValueError("package.json must be an object")
        locks = [name for name in NODE_LOCKS if (directory / name).exists()]
        spec = data.get("packageManager")
        manager, version = None, None
        if spec is not None:
            match = re.fullmatch(r"(npm|pnpm|yarn|bun)@(\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?)(?:\+sha[0-9]+\.[a-fA-F0-9]+)?", str(spec))
            if not match:
                problems.append("packageManager must name a supported manager and exact version")
            else:
                manager, version = match.groups()
        if len(locks) != 1:
            problems.append("Node project needs one unambiguous committed lockfile")
        elif manager and manager != NODE_LOCKS[locks[0]]:
            problems.append("packageManager conflicts with the lockfile")
        elif manager is None and spec is None:
            manager = NODE_LOCKS[locks[0]]
        if manager:
            if manager == "yarn" and not version:
                problems.append("Yarn major version is required to select classic or modern frozen install")
            groups.append({"ecosystem": "node", "manager": manager, "version": version, "lockfiles": locks,
                           "manifests": ["package.json"], "available": bool(shutil.which(manager)),
                           "note": "Project declaration and lockfile decide; personal preferences are not consulted."})
    pyproject = directory / "pyproject.toml"
    if pyproject.exists():
        path = local_file(root, pyproject.relative_to(root).as_posix())
        with path.open("rb") as stream:
            raw = stream.read(2 * 1024 * 1024 + 1)
        if len(raw) > 2 * 1024 * 1024:
            raise ValueError("pyproject exceeds size limit")
        data = tomllib.loads(raw.decode())
        project, tool = _table(data, "project"), _table(data, "tool")
        locks = [name for name in ("uv.lock", "poetry.lock") if (directory / name).exists()]
        if len(locks) > 1:
            problems.append("Python project has conflicting uv and Poetry lockfiles")
        elif locks:
            manager = "uv" if locks[0] == "uv.lock" else "poetry"
            groups.append({"ecosystem": "python", "manager": manager, "version": None, "lockfiles": locks,
                           "manifests": ["pyproject.toml"], "available": bool(shutil.which(manager)),
                           "requires_python": project.get("requires-python"),
                           "note": "Poetry is detected but needs its project-specific install workflow." if manager == "poetry" else "uv sync uses the committed lock."})
        elif project.get("dependencies") or tool.get("poetry"):
            problems.append("Python dependency project needs its chosen manager and lockfile")
    inputs = {}
    for group in groups:
        for name in [*group["lockfiles"], *group["manifests"]]:
            relative_file = (directory / name).relative_to(root).as_posix()
            inputs[relative_file] = sha(local_file(root, relative_file))
    for parent in directory.parents:
        if parent == root.parent:
            break
        if (parent / "pnpm-workspace.yaml").is_file() and any(g["manager"] == "pnpm" for g in groups):
            problems.append("Select the pnpm workspace root explicitly before installing")
        for manifest, ecosystem in (("package.json", "node"), ("pyproject.toml", "python")):
            if not (parent / manifest).is_file() or not any(g["ecosystem"] == ecosystem for g in groups):
                continue
            source = local_file(root, (parent / manifest).relative_to(root).as_posix())
            if source.stat().st_size > 2 * 1024 * 1024:
                raise ValueError("parent manifest exceeds size limit")
            data = load(source) if ecosystem == "node" else tomllib.loads(source.read_text())
            if not isinstance(data, dict):
                raise ValueError("parent manifest must be an object")
            workspace = data.get("workspaces") if ecosystem == "node" else _table(_table(data, "tool"), "uv").get("workspace")
            if workspace:
                problems.append("Select the declared workspace root explicitly before installing")
    return {"status": "needs_configuration" if problems else "passed", "directory": directory.relative_to(root).as_posix(),
            "groups": groups, "problems": problems, "inputs": inputs,
            "tools": {name: bool(shutil.which(name)) for name in ("git", "codex", "node", "npm", "uv", "psql")},
            "note": "Presence is not connectivity or authentication. No installer or package script ran."}


def install(root, relative=".", *, offline=False, allow_scripts=False):
    root = root.resolve()
    plan = inspect(root, relative)
    if plan["status"] != "passed":
        return plan
    if not plan["groups"]:
        return {**plan, "status": "needs_configuration", "reason": "no_locked_dependency_project"}
    # Preflight every group before making any dependency changes.
    commands = []
    environment = os.environ.copy()
    environment.update(COREPACK_ENABLE_NETWORK="0", UV_PYTHON_DOWNLOADS="never")
    for group in plan["groups"]:
        manager = group["manager"]
        executable = shutil.which(manager)
        if not executable:
            return {**plan, "status": "unavailable", "reason": "selected_package_manager_not_installed", "manager": manager}
        if manager == "poetry":
            return {**plan, "status": "needs_configuration", "reason": "use_project_poetry_workflow"}
        try:
            version = subprocess.run([executable, "--version"], capture_output=True, text=True, timeout=10, env=environment)
        except (OSError, subprocess.TimeoutExpired):
            return {**plan, "status": "unavailable", "reason": "cannot_verify_package_manager_version", "manager": manager}
        observed = version.stdout.strip()
        if manager == "uv":
            match = re.fullmatch(r"uv (\d+\.\d+\.\d+)(?: .*)?", observed)
            observed = match[1] if match else observed
        if version.returncode or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?", observed):
            return {**plan, "status": "unavailable", "reason": "cannot_verify_package_manager_version", "manager": manager}
        if group["version"] and observed != group["version"]:
            return {**plan, "status": "needs_configuration", "reason": "package_manager_version_mismatch", "manager": manager,
                    "expected": group["version"], "observed": observed}
        cache = inside(root, f".cache/{manager}")
        if manager == "npm":
            command = [executable, "ci", "--cache", str(cache), "--no-audit", "--no-fund"]
            if not allow_scripts:
                command.append("--ignore-scripts")
        elif manager == "pnpm":
            command = [executable, "install", "--frozen-lockfile", "--store-dir", str(cache)]
            if not allow_scripts:
                command.append("--ignore-scripts")
        elif manager == "bun":
            command = [executable, "install", "--frozen-lockfile", "--cache-dir", str(cache)]
            if not allow_scripts:
                command.append("--ignore-scripts")
        elif manager == "yarn":
            major = int(observed.split(".")[0])
            command = [executable, "install", "--frozen-lockfile" if major == 1 else "--immutable"]
            environment.update(YARN_CACHE_FOLDER=str(cache), YARN_ENABLE_GLOBAL_CACHE="false")
            if not allow_scripts:
                command += ["--ignore-scripts"] if major == 1 else ["--mode=skip-builds"]
        else:
            command = [executable, "sync", "--locked", "--cache-dir", str(cache)]
            environment["UV_PROJECT_ENVIRONMENT"] = str(inside(root, f"{relative}/.venv"))
            if not allow_scripts:
                command.append("--no-build")
        if offline:
            if manager not in {"npm", "pnpm", "uv"}:
                return {**plan, "status": "needs_configuration", "reason": "offline_mode_not_verified_for_manager", "manager": manager}
            command.append("--offline")
        commands.append((command, group))
    records = []
    for command, group in commands:
        log = runtime_path(root, f".runtime/setup/{uuid.uuid4().hex}.log")
        result = execute(command, cwd=_directory(root, relative), log=log, timeout=300, env=environment)
        records.append({"manager": group["manager"], "command": command, "log": log.relative_to(root).as_posix(), **result})
        if result["error"] or result["exit_code"]:
            return {**plan, "status": "failed", "results": records}
    unchanged = all(sha(local_file(root, p)) == digest for p, digest in plan["inputs"].items())
    return {**plan, "status": "passed" if unchanged else "stale", "results": records,
            "note": "Frozen dependency install only. Validate application build/tests separately; skipped build scripts may be required."}
