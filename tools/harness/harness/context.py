"""Explainable skill/reference selection, with optional actual file contents."""
from __future__ import annotations

from pathlib import Path
import re
import tomllib
import json

from .core import inside, matches
from .workflows import documents, load, selected_workflow, validate_conditions
from . import knowledge


def catalog(root: Path) -> dict:
    with (root / ".agents/context.toml").open("rb") as stream:
        data = tomllib.load(stream)
    if data.get("version") != 1 or not isinstance(data.get("skills"), list):
        raise ValueError("invalid context catalog")
    seen = set()
    for skill in data["skills"]:
        if not isinstance(skill, dict):
            raise ValueError("context skill must be a table")
        name = skill.get("name")
        if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) or name in seen:
            raise ValueError("context skill names must be unique")
        seen.add(name)
        entry = f".agents/skills/{name}/SKILL.md"
        documents(root, [entry], "skill entrypoint")
        resources = skill.get("references", [])
        if not isinstance(resources, list):
            raise ValueError("skill references must be an array")
        for rule in [skill, *resources]:
            if not isinstance(rule, dict):
                raise ValueError("context reference must be a table")
            validate_conditions(rule, "context catalog")
            if not isinstance(rule.get("when"), str) or not rule["when"].strip():
                raise ValueError("context selection needs a human-readable when condition")
            if not isinstance(rule.get("requires_skill", False), bool):
                raise ValueError("requires_skill must be a boolean")
        for ref in resources:
            relative = ref.get("file")
            if not isinstance(relative, str):
                raise ValueError("context reference requires a file")
            documents(root, [relative], "skill reference")
            if not inside(root, relative).is_relative_to(inside(root, f".agents/skills/{name}/references")):
                raise ValueError("skill references must live in that skill's references directory")
    folders = {p.name for p in (root / ".agents/skills").iterdir() if p.is_dir()}
    if seen != folders:
        raise ValueError("context catalog must cover exactly the repository skills")
    return data


def select(root: Path, kind: str, paths: list[str], topics: list[str], *, workflow=None, read=False) -> dict:
    config = catalog(root)
    for path in paths:
        inside(root, path)
    with (root / "tools/harness/harness.toml").open("rb") as stream:
        base = tomllib.load(stream)
    selected = selected_workflow(base, workflow)
    project = load(root, selected) if selected else None
    available = {topic for skill in config["skills"] for rule in [skill, *skill.get("references", [])]
                 for topic in rule.get("topics", [])}
    if project:
        project_context = project.get("context", {})
        available.update(project_context.get("topics", []))
        for rule in project_context.get("rules", []):
            available.update(rule.get("topics", []))
    project_scope = Path(selected).parent.name if selected else None
    for entry in knowledge.catalog(root)["entries"]:
        if entry["state"] == "adopted" and entry.get("project") in (None, project_scope):
            available.update(entry.get("topics", []))
    if set(topics) - available:
        raise ValueError("unknown context topics: " + ", ".join(sorted(set(topics) - available)))
    chosen = {}

    def add(relative, reason):
        chosen.setdefault(relative, []).append(reason)

    def triggered(rule):
        return (kind in rule.get("kinds", []) or bool(set(topics) & set(rule.get("topics", [])))
                or any(matches(p, rule.get("paths", [])) for p in paths))

    if (root / "AGENTS.md").is_file():
        add("AGENTS.md", "repository instructions")
    # Read small navigation maps before the selected bodies. Links are not
    # expanded here: the agent follows only those needed for the actual task.
    indexes = ["docs/index.md"]
    if selected:
        indexes.append(Path(selected).with_name("index.md").as_posix())
    for relative in dict.fromkeys(indexes):
        if (root / relative).is_file():
            documents(root, [relative], "document index")
            add(relative, "document index; follow only relevant links")
    if project:
        for document in project.get("context", {}).get("documents", []):
            add(document, "project workflow context")
        for rule in project.get("context", {}).get("rules", []):
            if triggered(rule):
                for document in rule.get("documents", []):
                    add(document, rule.get("when", "matching project context kind, topic or path"))

    for skill in config["skills"]:
        # Shared topics such as "async" refine an already relevant language
        # skill instead of pulling in every runtime's async manual.
        refs = [ref for ref in skill.get("references", []) if triggered(ref)]
        specific_ref = any(not ref.get("requires_skill", False) for ref in refs)
        if not triggered(skill) and not specific_ref:
            continue
        add(f".agents/skills/{skill['name']}/SKILL.md", skill["when"])
        for ref in refs:
            add(ref["file"], ref["when"])
    result = []
    for relative, reasons in chosen.items():
        record = {"path": relative, "reasons": reasons}
        if read:
            try:
                record["content"] = inside(root, relative).read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                record["read_status"] = "unavailable"
        result.append(record)
    for entry in knowledge.selected(root, kind, paths, topics, project_scope):
        record = {"path": knowledge.CATALOG, "entry_id": entry["id"], "content_scope": "knowledge_entry",
                  "reasons": ["adopted knowledge with matching scope and current evidence"]}
        if read:
            record["content"] = json.dumps(entry, ensure_ascii=False, indent=2)
        result.append(record)
    return {"status": "planned", "kind": kind, "paths": paths, "topics": topics,
            "workflow": selected, "documents": result,
            "security_review": project.get("security_review") if project else None,
            "note": "Read indexes to choose relevant source documents; links are not expanded. Missing or stale maps need targeted search. Explicit workflow documents and security context remain required. Paths match reading rules, not direct file requests. This is not dependency analysis or a model context injection hook."}
