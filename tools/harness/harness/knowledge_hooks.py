"""Codex hook adapter: bounded reviewed context and metadata-only checkpoints."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import knowledge
from .core import runtime_path
from .provenance import atomic, load, local_file, now, sha
from .workflows import selected_workflow
import tomllib


def handle(root, event, *, introduction=()):
    root = root.resolve()
    if not isinstance(event, dict) or event.get("hook_event_name") not in {"SessionStart", "PreCompact", "Stop"}:
        raise ValueError("unsupported knowledge hook event")
    name = event["hook_event_name"]
    session = event.get("session_id")
    if not isinstance(session, str) or not session or len(session) > 500:
        raise ValueError("knowledge hook needs a bounded session ID")
    session_hash = hashlib.sha256(session.encode()).hexdigest()[:24]
    if name == "SessionStart":
        with (root / "tools/harness/harness.toml").open("rb") as stream:
            workflow = selected_workflow(tomllib.load(stream))
        project = Path(workflow).parent.name if workflow else None
        entries = knowledge.selected(root, "plan", [], ["learning", "resume"], project)
        lines = ["작업 시작에는 AGENTS.md와 관련 과거 원문을 확인한다. 학습 기록은 과거 원문 확인을 대체하지 않는다.",
                 "필요한 지식은 tools/harness/run.py knowledge search와 context --read로 찾는다."]
        lines.extend(introduction)
        for event_name in ("Interrupt", "PreCompact"):
            checkpoint = runtime_path(root, f".runtime/knowledge-events/{session_hash}-{event_name}.json")
            if checkpoint.is_file():
                lines.append("이 세션의 재개 메타데이터: " + checkpoint.relative_to(root).as_posix())
        for entry in entries[:10]:
            # A partial instruction can discard the condition that made it safe.
            # Send the complete applicability unit, or a reference to its source.
            complete = json.dumps({key: entry.get(key, [] if key == "exclusions" else None)
                                   for key in ("id", "project", "lesson", "conditions", "exclusions")}, ensure_ascii=False)
            reference = f"지식 원문: python3 tools/harness/run.py knowledge show {entry['id']}"
            for candidate in (complete, reference):
                if len("\n".join([*lines, candidate])) <= 8000:
                    lines.append(candidate)
                    break
        return {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "\n".join(lines)}}
    tasks = []
    for path in sorted((root / "docs/tasks").glob("*/task.json"))[:100]:
        try:
            path = local_file(root, path.relative_to(root).as_posix())
        except ValueError:
            continue
        data = load(path, 128000)
        if not isinstance(data, dict):
            raise ValueError("task metadata must be an object")
        state = data.get('status')
        if not isinstance(state, str) or state not in {'planned', 'in_progress', 'needs_revision', 'blocked', 'complete'}:
            raise ValueError('unsupported task metadata state')
        if state != "complete":
            tasks.append({"path": path.relative_to(root).as_posix(), "sha256": sha(path), "state": state})
    checkpoint = {"version": 1, "event": name, "session_sha256": session_hash,
                  "created_at": now(), "tasks": tasks,
                  "note": "Metadata only. Read notes and originals for decisions; no transcript or tool payload was collected."}
    path = runtime_path(root, f".runtime/knowledge-events/{session_hash}-{name}.json")
    atomic(path, checkpoint)
    return {}
