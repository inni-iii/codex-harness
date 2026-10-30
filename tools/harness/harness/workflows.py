"""Portable project profiles; no framework, product or commands are guessed."""
from __future__ import annotations

import json
from pathlib import Path
import re
import tomllib

from .core import inside, validate_checks, validate_patterns
from .tasks import KINDS
from . import security_profiles


def validate_conditions(rule: dict, label: str) -> None:
    """A reading rule is an OR of explicit kinds, topics and relative paths."""
    for field in ("kinds", "topics", "paths"):
        values = rule.get(field, [])
        if not isinstance(values, list) or not all(isinstance(x, str) and x.strip() for x in values):
            raise ValueError(f"invalid {label} {field}")
        if field == "paths" and values:
            validate_patterns(values, f"{label} paths")
        if field == "kinds" and any(kind not in [*KINDS, "plan"] for kind in values):
            raise ValueError(f"unknown {label} kind")
    if not any(rule.get(field) for field in ("kinds", "topics", "paths")):
        raise ValueError(f"{label} needs at least one kind, topic or path condition")


def selected_workflow(config: dict, override: str | None = None) -> str | None:
    project = config.get("project", {})
    if not isinstance(project, dict):
        raise ValueError("project must be a table")
    value = override if override is not None else project.get("workflow")
    if value is not None and (not isinstance(value, str) or not value):
        raise ValueError("project.workflow must be a repository-relative file")
    return value


def validate_impacts(impacts, checks: list[dict]) -> None:
    if not isinstance(impacts, list):
        raise ValueError("impacts must be an array of tables")
    ids = {check["id"] for check in checks}
    for impact in impacts:
        if not isinstance(impact, dict):
            raise ValueError("impact must be a table")
        validate_patterns(impact.get("paths"), "impact paths")
        names = impact.get("checks")
        if not isinstance(names, list) or not names or not all(isinstance(n, str) and n in ids for n in names):
            raise ValueError("impact references unknown checks")
        if not isinstance(impact.get("reason"), str) or not impact["reason"].strip():
            raise ValueError("impact needs a reason")


def documents(root: Path, values, label="context documents", *, pending_document=None) -> list[str]:
    if not isinstance(values, list) or not all(isinstance(p, str) and p for p in values):
        raise ValueError(f"invalid {label}")
    for value in values:
        path = inside(root, value)
        if path.suffix != ".md" or (not path.is_file() and value != pending_document):
            raise ValueError(f"{label} must reference existing Markdown: {value}")
    return values


def load(root: Path, relative: str) -> dict:
    with inside(root, relative).open("rb") as stream:
        data = tomllib.load(stream)
    if data.get("version") != 1 or data.get("state") not in {"draft", "active"}:
        raise ValueError("workflow requires version=1 and state=draft or active")
    if not isinstance(data.get("name"), str) or not data["name"].strip():
        raise ValueError("workflow requires a project name")
    context = data.get("context", {})
    if not isinstance(context, dict):
        raise ValueError("workflow context must be a table")
    if set(context) - {"documents", "topics", "rules"}:
        raise ValueError("unknown workflow context fields")
    security_doc = data.get("security", {}).get("document") if isinstance(data.get("security"), dict) else None
    documents(root, context.get("documents", []), pending_document=security_doc)
    topics = context.get("topics", [])
    if not isinstance(topics, list) or not all(isinstance(t, str) and t for t in topics):
        raise ValueError("workflow context topics must be strings")
    rules = context.get("rules", [])
    if not isinstance(rules, list):
        raise ValueError("context.rules must be an array of tables")
    for rule in rules:
        if not isinstance(rule, dict):
            raise ValueError("context rule must be a table")
        if set(rule) - {"kinds", "topics", "paths", "documents", "when"}:
            raise ValueError("unknown project context rule fields")
        validate_conditions(rule, "project context rule")
        if "when" in rule and (not isinstance(rule["when"], str) or not rule["when"].strip()):
            raise ValueError("project context rule when must be a nonempty explanation")
        documents(root, rule.get("documents", []), pending_document=security_doc)
        if not rule.get("documents"):
            raise ValueError("project context rule needs documents")
    validate_checks(root, data.get("checks", []))
    # Cross-check IDs are checked after merging with the base registry.
    if data["state"] == "active" and not data.get("checks"):
        raise ValueError("active workflow must register real project checks")
    security = security_profiles.validate(root, data)
    if security and security.get("document"):
        # Read the reviewed design regardless of custom context path choices.
        data.setdefault("context", {}).setdefault("documents", [])
        if security["document"] not in data["context"]["documents"]:
            data["context"]["documents"].append(security["document"])
    return data


def create(root: Path, slug: str, goal: str) -> Path:
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug) or not goal.strip():
        raise ValueError("project requires a lowercase slug and nonempty goal")
    relative = f"docs/projects/{slug}"
    inside(root, relative)  # Resolve for containment; preserve the caller's root spelling in the return path.
    directory = root / relative
    if directory.exists():
        raise FileExistsError(f"project already exists: {slug}")
    template = (root / ".agents/skills/plan-project/assets/project-workflow.toml").read_text()
    brief_template = (root / ".agents/skills/plan-project/assets/project-brief.md").read_text()
    security_template = (root / ".agents/skills/security-review/assets/security-profile.md").read_text()
    index_template = (root / ".agents/skills/plan-project/assets/project-index.md.tmpl").read_text()
    content = template.replace('name = "example"', 'name = ' + json.dumps(slug))
    content = content.replace('docs/projects/example/brief.md', f'docs/projects/{slug}/brief.md')
    content = content.replace('docs/projects/example/security.md', f'docs/projects/{slug}/security.md')
    content = content.replace('docs/projects/example/index.md', f'docs/projects/{slug}/index.md')
    directory.mkdir(parents=True)
    (directory / "brief.md").write_text(f"# {slug}\n\n목표: {goal.strip()}\n\n" + brief_template)
    (directory / "security.md").write_text(security_template)
    (directory / "index.md").write_text(index_template.replace("{{project}}", slug))
    path = directory / "workflow.toml"
    path.write_text(content)
    return path
