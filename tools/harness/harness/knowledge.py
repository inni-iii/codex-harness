"""Portable, reviewed lessons. Reads never create a registry or a home directory."""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
import json
import os
from pathlib import Path
import re
from urllib.parse import urlsplit

from .core import inside, matches, runtime_path
from .provenance import atomic, load, local_file, now, sha, signature
from .security import PATTERNS, _candidate

CATALOG = "docs/knowledge/catalog.json"
LIMIT = 2 * 1024 * 1024
STATES = {"candidate", "evaluated", "adopted", "superseded"}
FIELDS = {"id", "title", "lesson", "conditions", "exclusions", "project", "topics", "paths", "kinds", "sources"}


def slug(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value) or len(value) > 100:
        raise ValueError("knowledge IDs and project scopes need lowercase slugs")
    return value


def safe_text(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 16000:
        raise ValueError("knowledge text is empty or exceeds its limit")
    if any(_candidate(pattern, value) for pattern in PATTERNS.values()):
        raise ValueError("possible credential in knowledge input; remove it before recording")
    return value


def _path(root):
    target = inside(root, CATALOG)
    cursor = root
    for part in Path(CATALOG).parts:
        cursor /= part
        if cursor.is_symlink():
            raise ValueError("knowledge catalog symlinks are unsupported")
    return target


def validate(entry):
    if not isinstance(entry, dict) or set(entry) - (FIELDS | {"state", "history", "evidence", "origin"}):
        raise ValueError("unsupported knowledge entry fields")
    if not {"state", "history", "evidence"} <= set(entry):
        raise ValueError("stored knowledge needs explicit review metadata")
    for key in ("id",):
        slug(entry.get(key))
    if entry.get("project") is not None:
        slug(entry["project"])
    for key in ("title", "lesson", "conditions"):
        safe_text(entry.get(key))
    for key in ("exclusions", "topics", "paths", "kinds", "sources"):
        values = entry.get(key, [])
        if not isinstance(values, list) or len(values) > 100:
            raise ValueError("invalid knowledge list")
        for value in values:
            safe_text(value)
    from .core import validate_patterns
    from .tasks import KINDS
    if entry.get("paths"):
        validate_patterns(entry["paths"], "knowledge paths")
    if set(entry.get("kinds", [])) - {*KINDS, "plan"}:
        raise ValueError("unknown knowledge task kind")
    for source in entry.get("sources", []):
        parsed = urlsplit(source)
        if parsed.scheme:
            if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
                raise ValueError("knowledge sources need HTTPS without embedded credentials")
        elif Path(source).is_absolute() or ".." in Path(source).parts:
            raise ValueError("knowledge sources need portable relative paths")
    if not isinstance(entry.get("state"), str) or entry["state"] not in STATES:
        raise ValueError("invalid knowledge state")
    if not isinstance(entry.get("history", []), list) or not isinstance(entry.get("evidence", []), list):
        raise ValueError("invalid knowledge history or evidence")
    for item in entry["history"]:
        if (not isinstance(item, dict) or not isinstance(item.get("at"), str)
                or not isinstance(item.get("action"), str)
                or item["action"] not in STATES | {"created", "imported"}):
            raise ValueError("invalid knowledge history event")
    for evidence in entry.get("evidence", []):
        if (not isinstance(evidence, dict) or set(evidence) != {"path", "sha256"}
                or not isinstance(evidence["path"], str) or Path(evidence["path"]).is_absolute()
                or ".." in Path(evidence["path"]).parts
                or not re.fullmatch(r"[a-f0-9]{64}", str(evidence["sha256"]))):
            raise ValueError("invalid knowledge evidence reference")
    if entry.get("state") in {"evaluated", "adopted"} and not entry.get("evidence"):
        raise ValueError("reviewed knowledge needs content-bound evidence")
    # Also bound/inspect metadata imported from another installation.
    encoded = json.dumps(entry, ensure_ascii=False, allow_nan=False)
    if len(encoded.encode()) > 64000:
        raise ValueError("knowledge entry exceeds size limit")
    if any(_candidate(pattern, encoded) for pattern in PATTERNS.values()):
        raise ValueError("possible credential in knowledge metadata")
    return entry


def catalog(root):
    path = _path(root)
    if not path.exists():
        return {"version": 1, "entries": []}
    data = load(path, LIMIT)
    if not isinstance(data, dict) or set(data) != {"version", "entries"} or data["version"] != 1 or not isinstance(data["entries"], list):
        raise ValueError("invalid knowledge catalog")
    if len(data["entries"]) > 2000:
        raise ValueError("knowledge catalog entry limit exceeded")
    ids = []
    for entry in data["entries"]:
        validate(entry)
        ids.append(entry["id"])
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate knowledge IDs")
    return data


def _check_document_size(data):
    # Match provenance.atomic's indented UTF-8 and platform newline encoding.
    encoded = json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if len(encoded.replace("\n", os.linesep).encode("utf-8")) > LIMIT:
        raise ValueError("serialized knowledge document exceeds size limit")


@contextmanager
def _write(root):
    lock = runtime_path(root, ".runtime/knowledge.lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ValueError("knowledge writer is active; retry after it finishes") from exc
    try:
        os.close(fd)
        data = catalog(root)
        yield data
        if len(data["entries"]) > 2000:
            raise ValueError("knowledge catalog entry limit exceeded")
        for entry in data["entries"]:
            validate(entry)
        _check_document_size(data)
        atomic(_path(root), data)
    finally:
        lock.unlink(missing_ok=True)


def _entry(data, identity):
    slug(identity)
    for entry in data["entries"]:
        if entry["id"] == identity:
            return entry
    raise ValueError("knowledge entry not found")


def add(root, spec, *, origin=None):
    if not isinstance(spec, dict) or set(spec) - FIELDS:
        raise ValueError("new knowledge accepts lesson fields only; review state is assigned separately")
    item = deepcopy(spec)
    item.update(state="candidate", evidence=[], history=[{"at": now(), "action": "created"}])
    if origin:
        item["origin"] = origin
    validate(item)
    with _write(root) as data:
        if any(e["id"] == item["id"] for e in data["entries"]):
            raise ValueError("knowledge ID already exists")
        data["entries"].append(item)
    return {"status": "created", "entry": item}


def listing(root, *, project=None, state=None, query=None):
    if project is not None:
        slug(project)
    if state is not None and state not in STATES:
        raise ValueError("invalid knowledge state")
    entries = [e for e in catalog(root)["entries"]
               if (project is None or e.get("project") in (None, project)) and (state is None or e["state"] == state)]
    if query:
        terms = query.casefold().split()
        entries = [e for e in entries if all(t in json.dumps(e, ensure_ascii=False).casefold() for t in terms)]
    return {"status": "passed", "entries": entries, "count": len(entries)}


def review(root, identity, state, reason, evidence=(), replacement=None):
    if state not in {"evaluated", "adopted", "superseded"}:
        raise ValueError("invalid knowledge review transition")
    safe_text(reason)
    proofs = [{"path": p, "sha256": sha(local_file(root, p))} for p in evidence]
    with _write(root) as data:
        entry = _entry(data, identity)
        if entry["state"] == "superseded":
            raise ValueError("superseded knowledge must remain historical")
        if state == "evaluated" and entry["state"] != "candidate":
            raise ValueError("only a candidate can enter evaluated state")
        if state == "adopted" and entry["state"] not in {"candidate", "evaluated", "adopted"}:
            raise ValueError("invalid adoption state")
        if state != "superseded" and not proofs:
            raise ValueError("review needs actual evidence paths")
        if state == "superseded":
            successor = _entry(data, replacement)
            if successor["id"] == identity or successor["state"] != "adopted" or successor.get("project") != entry.get("project"):
                raise ValueError("replacement must be another adopted entry in the same scope")
        entry["state"] = state
        entry["evidence"] = proofs if state != "superseded" else entry["evidence"]
        entry["history"].append({"at": now(), "action": state, "reason": reason, "replacement": replacement})
    return {"status": "passed", "entry": entry,
            "note": "Evidence identity is checked; the reviewer remains responsible for what it proves."}


def promote(root, identity, new_id, reason):
    slug(new_id)
    safe_text(reason)
    source = deepcopy(_entry(catalog(root), identity))
    if source.get("project") is None or source["state"] != "adopted":
        raise ValueError("promotion starts from adopted project knowledge")
    spec = {k: v for k, v in source.items() if k in FIELDS}
    spec.update(id=new_id, project=None)
    # Promotion creates a candidate; project evidence is not proof of generality.
    spec["sources"] = [*spec.get("sources", []), CATALOG + "#" + identity]
    return add(root, spec, origin={"promoted_from": identity, "reason": reason})


def export(root, output, *, project=None):
    entries = listing(root, project=project, state="adopted")["entries"]
    payload = {"version": 1, "entries": entries}
    bundle = {"payload": payload, "sha256": signature(payload)}
    path = inside(root, output)
    if path.exists() or output == CATALOG:
        raise ValueError("knowledge export refuses to overwrite an existing path")
    cursor = root
    for part in Path(output).parts:
        cursor /= part
        if cursor.is_symlink():
            raise ValueError("knowledge export symlinks are unsupported")
    _check_document_size(bundle)
    atomic(path, bundle)
    return {"status": "created", "path": output, "count": len(entries)}


def import_bundle(root, path, *, dry_run=False):
    bundle = load(local_file(root, path), LIMIT)
    if not isinstance(bundle, dict) or set(bundle) != {"payload", "sha256"} or signature(bundle["payload"]) != bundle["sha256"]:
        raise ValueError("knowledge bundle integrity mismatch")
    payload = bundle["payload"]
    if not isinstance(payload, dict) or set(payload) != {"version", "entries"} or payload["version"] != 1 or not isinstance(payload["entries"], list):
        raise ValueError("invalid knowledge bundle")
    incoming, seen = [], set()
    for entry in payload["entries"]:
        validate(entry)
        if entry["id"] in seen:
            raise ValueError("duplicate bundle knowledge IDs")
        seen.add(entry["id"])
        item = deepcopy(entry)
        item.update(state="candidate", evidence=[], history=[{"at": now(), "action": "imported"}],
                    origin={"bundle_sha256": bundle["sha256"], "state": entry["state"]})
        incoming.append(item)

    def merge(data, commit):
        existing = {e["id"]: e for e in data["entries"]}
        conflicts, added, skipped = [], [], []
        for item in incoming:
            previous = existing.get(item["id"])
            if previous:
                before = {k: v for k, v in previous.items() if k in FIELDS}
                after = {k: v for k, v in item.items() if k in FIELDS}
                (skipped if before == after else conflicts).append(item["id"])
            else:
                added.append(item)
        if commit and not conflicts:
            data["entries"].extend(added)
        return {"status": "needs_review" if conflicts else "planned" if dry_run else "passed",
                "added": [e["id"] for e in added], "skipped": skipped, "conflicts": conflicts,
                "note": "Imported entries remain candidates. A checksum is not an authenticity guarantee."}

    if dry_run:
        return merge(catalog(root), False)
    # Reject conflicts before opening a writer; failed imports do not rewrite the catalog.
    result = merge(catalog(root), False)
    if result["conflicts"]:
        return result
    with _write(root) as data:
        result = merge(data, True)
        if result["conflicts"]:
            raise ValueError("knowledge changed while importing; retry the preview")
    return result


def selected(root, kind, paths, topics, project=None):
    chosen = []
    for entry in catalog(root)["entries"]:
        if entry["state"] != "adopted" or entry.get("project") not in (None, project):
            continue
        if (kind in entry.get("kinds", []) or set(topics) & set(entry.get("topics", []))
                or any(matches(p, entry.get("paths", [])) for p in paths)):
            valid = all((root / e["path"]).is_file() and sha(local_file(root, e["path"])) == e["sha256"] for e in entry["evidence"])
            if valid:
                chosen.append(entry)
    return chosen


def show(root, identity):
    return {"status": "passed", "entry": _entry(catalog(root), identity)}
