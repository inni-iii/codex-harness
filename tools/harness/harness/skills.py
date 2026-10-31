"""Create native repository skills and register selective reading atomically."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import tempfile

from . import context, flow_catalog, knowledge
from .core import inside, runtime_path
from .provenance import local_file, sha


def validate(path):
    text = path.read_text(encoding="utf-8")
    match = re.match(r'---\nname: ([a-z0-9-]+)\ndescription: ([^\n]+)\n---\n(.+)', text, re.S)
    if not match or match[1] != path.parent.name:
        raise ValueError("invalid repository skill metadata")
    # This repository emits the minimal standard format, not a general YAML parser.
    if len(match[2].splitlines()) != 1 or not match[3].strip() or re.search(r"(?m)^\s*\[TODO:", match[3]):
        raise ValueError("skill body or metadata is unfinished")
    description = json.loads(match[2]) if match[2].startswith('"') else match[2]
    if not isinstance(description, str) or not description.strip() or len(description) > 1024:
        raise ValueError("invalid skill description")
    return {"status": "passed", "name": match[1], "path": str(path), "scope": "minimal_repository_format"}


def _replace_text(path, text):
    fd, temporary = tempfile.mkstemp(prefix=".skill-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def create(root, name, description, body, *, topics=(), kinds=(), paths=()):
    knowledge.slug(name)
    if len(name) > 64 or "\n" in description or not description.strip() or len(description) > 1024:
        raise ValueError("invalid skill name or description")
    knowledge.safe_text(body)
    knowledge.safe_text(description)
    context.catalog(root)
    has_flow = (root / flow_catalog.CATALOG).is_file()
    if has_flow:
        flow_catalog.load(root)
    folder = inside(root, f".agents/skills/{name}")
    parent = root / ".agents/skills"
    if parent.is_symlink() or (root / ".agents").is_symlink() or folder.exists():
        raise ValueError("skill destination already exists or is aliased")
    registry = local_file(root, ".agents/context.toml")
    before = registry.read_text()
    rule = {"topics": list(topics) or [name], "kinds": list(kinds), "paths": list(paths)}
    from .workflows import validate_conditions
    validate_conditions(rule, "new skill")
    text = f'---\nname: {name}\ndescription: {json.dumps(description, ensure_ascii=False)}\n---\n\n{body.strip()}\n'
    addition = '\n[[skills]]\nname = ' + json.dumps(name) + '\nwhen = ' + json.dumps(description, ensure_ascii=False) + '\n'
    for field, values in rule.items():
        if values:
            addition += field + " = " + json.dumps(values, ensure_ascii=False) + "\n"
    lock = runtime_path(root, ".runtime/skills.lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ValueError("another skill writer is active") from exc
    route_kind = rule["kinds"][0] if rule["kinds"] else "review"
    gated = route_kind in {"implement", "debug"}
    created = False
    try:
        os.close(fd)
        if registry.read_text() != before:
            raise ValueError("skill registry changed; re-read before creating")
        folder.mkdir()
        created = True
        (folder / "SKILL.md").write_text(text)
        validate(folder / "SKILL.md")
        if has_flow:
            (folder / 'routes.toml').write_text(
                'version=1\n[[routes]]\nname="main"\nwhen=' + json.dumps(description, ensure_ascii=False)
                + '\nkind=' + json.dumps(route_kind) + '\ninputs=' + json.dumps(['request', 'design', 'alignment'] if gated else ['request'])
                + ('\nentry_checks=["alignment"]' if gated else '') + '\ndocuments=[]\n'
                  'validation="Compare the requested result and actual evidence using SKILL.md."\n'
                  'evidence_types=["artifact"]\nrequired_calls=[]\nfinish=true\n'
                  '[[routes.steps]]\nid="execute"\ninstruction="Perform the scoped procedure in SKILL.md and record actual evidence."\n')
        _replace_text(registry, before + addition)
        context.catalog(root)
        if has_flow:
            flow_catalog.load(root)
    except Exception:
        if registry.read_text() == before + addition:
            _replace_text(registry, before)
        if created:
            (folder / "SKILL.md").unlink(missing_ok=True)
            (folder / "routes.toml").unlink(missing_ok=True)
            folder.rmdir()
        raise
    finally:
        lock.unlink(missing_ok=True)
    return {"status": "created", "skill": f".agents/skills/{name}/SKILL.md", "topics": rule["topics"],
            "note": "Native skill and reading rule created. Validate behavior with the intended task; discovery alone is not quality evidence."}


def from_knowledge(root, identity, name, description):
    entry = knowledge.show(root, identity)["entry"]
    if entry["state"] != "adopted" or entry.get("project") is not None:
        raise ValueError("shared skills require adopted common knowledge; keep project facts in project documents")
    if not all(sha(local_file(root, e["path"])) == e["sha256"] for e in entry["evidence"]):
        raise ValueError("knowledge evidence changed; review before generating a skill")
    body = (f"# {entry['title']}\n\n적용 조건: {entry['conditions']}\n\n{entry['lesson']}\n\n"
            + "\n".join("적용 제외: " + e for e in entry.get("exclusions", []))
            + f"\n\n근거와 변경 이력: [학습 기록](../../../{knowledge.CATALOG})의 ID `{identity}`.\n"
              "이 기록이 대체되거나 조건이 바뀌면 스킬과 선택 규칙도 함께 검토한다.\n")
    return create(root, name, description, body, topics=entry.get("topics", []),
                  kinds=entry.get("kinds", []), paths=entry.get("paths", []))
