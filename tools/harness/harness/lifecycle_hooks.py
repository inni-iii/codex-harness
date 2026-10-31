"""Bounded local lifecycle helpers: reminders, interruption and static checks."""
from __future__ import annotations

import json
from pathlib import Path
import sys

from . import hook_sessions as sessions, knowledge_hooks, remote_guard
from .core import files, runtime_path, strict_json
from .evidence import task_file
from .provenance import atomic, load, local_file, now, sha, signature

EVENTS = {"SessionStart", "PreCompact", "Stop", "Interrupt", "PreToolUse", "PostToolUse"}
INPUT_LIMIT = 2 * 1024 * 1024


def _watched(relative):
    path = Path(relative)
    return (relative in {"AGENTS.md", "README.md", "tools/harness/harness.toml"}
            or relative.startswith(".codex/") and path.suffix in {".json", ".toml"}
            or relative.startswith((".agents/", "docs/", "tools/harness/docs/")) and path.suffix in {".md", ".toml", ".json"}
            or relative.startswith(("tools/harness/harness/", "tools/harness/scripts/")) and path.suffix == ".py")


def _inventory(root, *, watched):
    result, size = {}, 0
    for path in files(root):
        relative = path.relative_to(root).as_posix()
        if watched and not _watched(relative):
            continue
        length = path.stat().st_size
        size += length
        if len(result) >= 2000 or length > 2 * 1024 * 1024 or size > 32 * 1024 * 1024:
            raise ValueError("hook source inventory exceeds limit")
        result[relative] = [sha(path), path.stat().st_mode & 0o111]
    return result


def _checkpoint(root, key, state, event):
    result = {"version": 1, "event": event, "session_sha256": key, "created_at": now(), "tasks": []}
    slug = state.get("task")
    if slug:
        try:
            path = task_file(root, slug)
            data = load(path, 128000)
            status = data.get("status") if isinstance(data, dict) else None
            if not isinstance(status, str) or status not in {"planned", "in_progress", "needs_revision", "blocked", "complete"}:
                raise ValueError("invalid task state")
            result["tasks"].append({"path": path.relative_to(root).as_posix(), "sha256": sha(path), "state": status})
            notes = path.parent / "notes.md"
            if notes.is_file() and notes.stat().st_size <= 128000:
                result["notes"] = {"path": notes.relative_to(root).as_posix(), "sha256": sha(local_file(root, notes.relative_to(root).as_posix()))}
        except (OSError, ValueError):
            result["task_unavailable"] = True
    validation = state.get("validation")
    if isinstance(validation, dict):
        result["last_static_check"] = {k: validation[k] for k in ("status", "checks", "at", "report") if k in validation}
    result["note"] = "Explicit task binding only; no prompt, transcript, tool payload or summary collected."
    atomic(runtime_path(root, f".runtime/knowledge-events/{key}-{event}.json"), result)


def _stop(root, key, state):
    slug = state.get("task")
    if not slug:
        return {}
    try:
        path = task_file(root, slug)
        task = load(path, 128000)
        if not isinstance(task, dict):
            raise ValueError("task must be an object")
        if task.get("status") == "complete":
            state["task"] = None
            state.pop("stop_notice", None)
            return {}
        from . import evidence
        from .provenance import environment
        stamp = signature({"task": slug, "sources": _inventory(root, watched=False), "environment": environment()})
        issues = []
        if evidence.assess(root, path, task):
            issues.append("검증·리뷰 근거 연결 또는 현재 소스와의 일치 확인이 남아 있어")
        notes = path.parent / "notes.md"
        if (not notes.is_file() or notes.stat().st_size > 128000
                or not local_file(root, notes.relative_to(root).as_posix()).read_text().strip()
                or not isinstance(task.get("next_action"), str) or not task["next_action"].strip()):
            issues.append("인수인계 기록과 다음 행동을 확인해")
    except (OSError, ValueError, TypeError, KeyError):
        stamp = signature({"task": slug, "unavailable": True})
        previous = state.get("stop_notice", {})
        if isinstance(previous, dict) and previous.get("stamp") == stamp:
            return {}
        issues = ["작업 기록·근거를 훅의 크기/경로 한도 안에서 확인하지 못했어"]
    previous = state.get("stop_notice", {})
    if isinstance(previous, dict) and previous.get("stamp") == stamp and previous.get("issues") == len(issues):
        return {}
    state["stop_notice"] = {"stamp": stamp, "issues": len(issues), "at": now()}
    if not issues:
        return {}
    return {"systemMessage": f"연결된 작업 {slug}: " + "; ".join(issues)
            + f". python3 tools/harness/run.py evidence verify {slug}로 확인해. 알림만 제공하며 자동 재실행·완료 처리는 하지 않아."}


def _post(root, key, state, event):
    if event.get("tool_name") not in {"Bash", "exec_command", "apply_patch", "Edit", "Write"}:
        return {}
    current = _inventory(root, watched=True)
    previous = state.get("watched")
    if previous is not None and not isinstance(previous, dict):
        raise ValueError("invalid hook validation baseline")
    changed = sorted(p for p in current.keys() | (previous or {}).keys() if current.get(p) != (previous or {}).get(p))
    if not changed:
        return {}
    from . import agent_config, doctor
    results = {"doctor": doctor.inspect(root)}
    config_changed = previous is None or any(p.startswith(".codex/") or p.endswith("/agent_config.py") for p in changed)
    if config_changed:
        results["agent-config"] = agent_config.inspect(root)
    # No configured check commands, package scripts, models or network calls.
    stable = current == _inventory(root, watched=True)
    passed = all(r.get("status") == "passed" for r in results.values())
    report = f".runtime/hook-checks/{key}.json"
    record = {"version": 1, "at": now(), "status": "stale" if not stable else "passed" if passed else "findings",
              "checks": list(results), "changed_paths": changed[:50], "changed_count": len(changed),
              "results": {name: {"status": value.get("status"), "error_count": len(value.get("errors", [])),
                                  "finding_count": len(value.get("findings", []))} for name, value in results.items()},
              "report": report, "note": "Static configuration/link/syntax checks only; not behavior evidence."}
    atomic(runtime_path(root, report), record)
    state["validation"] = record
    if stable:
        state["watched"] = current
    if record["status"] == "passed":
        return {}
    return {"systemMessage": "변경 후 정적 검사에 확인할 항목이 있어. " + report
            + "에서 상태를 보고 doctor/security config로 상세 확인해. 전체 테스트나 자동 수정은 실행하지 않았어."}


def handle(root, event):
    root = root.resolve()
    if not isinstance(event, dict) or not isinstance(event.get("hook_event_name"), str) or event["hook_event_name"] not in EVENTS:
        raise ValueError("unsupported lifecycle hook event")
    name = event["hook_event_name"]
    key = sessions.session_key(event.get("session_id"))
    if name == "PreToolUse":
        if event.get("tool_name") not in {"Bash", "exec_command"}:
            return {}
        tool = event.get("tool_input")
        if not isinstance(tool, dict):
            raise ValueError("missing shell hook input")
        command = tool.get("command", tool.get("cmd"))
        cwd = tool.get("workdir", event.get("cwd", str(root)))
        rule = remote_guard.inspect(root, command, cwd=cwd)
        if rule:
            return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                    "permissionDecisionReason": f"SSH 서버는 읽기 전용이므로 명시적인 원격 변경/업로드를 차단했어 ({rule}). 로컬 수정안 또는 원격 소유자에게 전달할 지침을 준비해."}}
        return {}
    if name == "PreCompact":
        return knowledge_hooks.handle(root, event)
    if name == "Interrupt":
        # Atomic state reads let an interruption record survive a busy checker.
        # This writes only the separate checkpoint, never the session cache.
        _checkpoint(root, key, sessions.read(root, key), name)
        return {}
    with sessions.lock(root, key) as acquired:
        if not acquired:
            return {}  # Another callback owns state; never wait or continue a turn.
        state = sessions.read(root, key)
        if name == "SessionStart":
            state.setdefault("watched", _inventory(root, watched=True))
            hints = [f"작업 기록을 만들었다면 연결: python3 tools/harness/run.py hook bind <task> --session-key {key}. 짧은 질문에는 task 생성을 강제하지 않는다."]
            if state.get("task"):
                hints.append("이 세션에 연결된 작업: " + state["task"])
            result = knowledge_hooks.handle(root, event, introduction=hints)
        elif name == "Stop":
            _checkpoint(root, key, state, name)
            result = _stop(root, key, state)
        else:
            result = _post(root, key, state, event)
        sessions.save(root, key, state)
        return result


def main(root):
    try:
        raw = sys.stdin.buffer.read(INPUT_LIMIT + 1)
        if len(raw) > INPUT_LIMIT:
            raise ValueError("hook input exceeds limit")
        result = handle(root, strict_json(raw.decode()))
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError, UnicodeError):
        print("lifecycle hook could not verify this event; normal host permissions still apply", file=sys.stderr)
        return 1
