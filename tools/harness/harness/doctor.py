"""Read-only static checks. Connectivity is a separate opt-in operation."""
from __future__ import annotations

import ast
import json
from pathlib import Path
import re
import shutil
import tomllib
from urllib.parse import unquote

from .core import files, manifest, strict_json
from .tasks import validate as validate_task
from . import context, knowledge, workflows


def inspect(root: Path) -> dict:
    errors, notes = [], []
    for relative in ["AGENTS.md", "tools/harness/run.py", "tools/harness/harness.toml"]:
        if not (root / relative).is_file():
            errors.append(f"missing required file: {relative}")
    try:
        config = manifest(root)
        stack = config.get("stack")
        base_stack = {"frontend": "svelte", "backend": "python"}
        # Older portable profiles may omit the newly agreed database field.
        if stack not in (base_stack, {**base_stack, "database": "postgresql"}):
            errors.append("agreed base stack is Svelte/Python with PostgreSQL when database is declared")
    except (ValueError, OSError, tomllib.TOMLDecodeError) as exc:
        errors.append(str(exc))
    try:
        codex = tomllib.loads((root / ".codex/config.toml").read_text())
        servers = codex.get("mcp_servers", {})
        expected = {"openaiDeveloperDocs": "https://developers.openai.com/mcp", "svelte": "https://mcp.svelte.dev/mcp"}
        for name, url in expected.items():
            if servers.get(name, {}).get("url") != url:
                errors.append(f"MCP configuration mismatch: {name}")
        if any(k in codex for k in ["model", "model_provider", "approval_policy", "sandbox_mode"]):
            errors.append("shared Codex config must not impose model/auth/permission defaults")
        hooks = codex.get("hooks", {}).get("UserPromptSubmit", [])
        hooks_path = root / ".codex/hooks.json"
        if hooks_path.is_file():
            hooks = hooks + strict_json(hooks_path.read_text()).get("hooks", {}).get("UserPromptSubmit", [])
        if hooks:
            if codex.get("features", {}).get("hooks") is not True:
                errors.append("routing hook is configured but hooks feature is not enabled")
            if not (root / "tools/harness/route_prompt.py").is_file():
                errors.append("routing hook entrypoint is missing")
            notes.append("routing hook: configured; host support and /hooks trust are unverified; run/chat execute routing directly")
        else:
            notes.append("routing hook: not registered; model routing is optional")
    except (ValueError, OSError, tomllib.TOMLDecodeError) as exc:
        errors.append(f"MCP configuration: {exc}")
    for path in files(root):
        relative = path.relative_to(root).as_posix()
        try:
            if path.suffix == ".py":
                ast.parse(path.read_text(encoding="utf-8"), filename=relative)
            if path.suffix == ".toml":
                tomllib.loads(path.read_text(encoding="utf-8"))
            if path.suffix == ".json":
                data = strict_json(path.read_text(encoding="utf-8"))
                if relative.startswith("docs/tasks/") and path.name == "task.json":
                    entries = data.get('evidence', {}) if isinstance(data, dict) else {}
                    missing_local = (data.get('status') == 'complete' and isinstance(entries, dict) and
                                     any(isinstance(e, dict) and isinstance(e.get('path'), str)
                                         and e['path'].startswith('.runtime/') and not (root / e['path']).is_file()
                                         for e in entries.values())) if isinstance(data, dict) else False
                    errors.extend(f"{relative}: {e}" for e in validate_task(data, root=root, task_path=path,
                                                                          allow_missing_runtime=missing_local))
                    if missing_local:
                        notes.append(f'{relative}: historical local artifacts unavailable; evidence is unverified here; rerun before reuse')
            if path.suffix != ".md":
                continue
            text = path.read_text(encoding="utf-8")
            if path.name == "SKILL.md":
                match = re.match(r'---\nname: ([a-z0-9-]+)\ndescription: (.+)\n---', text)
                if not match or match[1] != path.parent.name:
                    errors.append(f"invalid skill metadata: {relative}")
            # Ignore illustrative code blocks; validate actual relative Markdown links.
            prose = re.sub(r"```.*?```", "", text, flags=re.S)
            for target in re.findall(r"\]\(([^)\s]+)\)", prose):
                if "://" in target or target.startswith(("#", "mailto:")):
                    continue
                if target.startswith("/"):
                    errors.append(f"nonportable absolute link: {relative}")
                    continue
                dest = (path.parent / unquote(target.split('#')[0])).resolve()
                if not dest.is_relative_to(root.resolve()) or not dest.exists():
                    errors.append(f"broken/outside link in {relative}: {target}")
        except (OSError, ValueError, SyntaxError, UnicodeError) as exc:
            errors.append(f"{relative}: {exc}")
    skills = root / ".agents/skills"
    try:
        knowledge.catalog(root)
    except (OSError, ValueError) as exc:
        errors.append(f"knowledge catalog: {exc}")
    if not skills.is_dir() or not any(skills.iterdir()):
        errors.append("no canonical project skills")
    else:
        for folder in skills.iterdir():
            if folder.is_dir() and not (folder / "SKILL.md").is_file():
                errors.append(f"missing SKILL.md: {folder.name}")
    if (root / ".agents/context.toml").is_file():
        try:
            context.catalog(root)
        except (OSError, ValueError) as exc:
            errors.append(f"context catalog: {exc}")
    for profile in sorted((root / "docs/projects").glob("*/workflow.toml")):
        try:
            relative = profile.relative_to(root).as_posix()
            workflows.load(root, relative)
            manifest(root, relative)
        except (OSError, ValueError) as exc:
            errors.append(f"{profile.relative_to(root)}: {exc}")
    try:
        package = json.loads((root / "tools/harness/browser/package.json").read_text())
        lock = json.loads((root / "tools/harness/browser/package-lock.json").read_text())
        if lock["packages"][""]["dependencies"] != package["dependencies"]:
            errors.append("browser dependency manifest/lock mismatch")
    except (OSError, ValueError, KeyError) as exc:
        errors.append(f"browser lock validation: {exc}")
    for exe in ["git", "codex", "node", "npm"]:
        notes.append(f"{exe}: {'available' if shutil.which(exe) else 'not found (needed only for related tools)'}")
    try:
        import xml.etree.ElementTree as xml_tree
        xml_tree.fromstring("<testsuite/>")
        notes.append("JUnit XML parser: available")
    except ImportError:
        notes.append("JUnit XML parser: unavailable; repair this Python's Expat linkage or use a working interpreter before JUnit checks")
    notes.append("static checks do not prove client trust, MCP connectivity, authentication or product behavior")
    return {"status": "failed" if errors else "passed", "errors": errors, "notes": notes}
