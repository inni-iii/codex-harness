"""Bounded unresolved-hook feedback; never execute repairs, checks or models."""
from __future__ import annotations

import hashlib
import json
import re
import stat

from .core import runtime_path, strict_json
from .provenance import atomic, load, now

EVENTS = ("SessionStart", "PreCompact", "Stop", "Interrupt", "PreToolUse", "PostToolUse")
ISSUES = (*EVENTS, "StaticCheck")
STAGES = {"input_read", "input_limit", "input_decode", "input_parse", "workspace", "event", "session_key",
          "shell_input", "remote_guard", "checkpoint", "state_read", "state_lock", "source_inventory",
          "context", "task_assessment", "doctor", "agent_config", "source_recheck", "static_report_write",
          "state_write", "state_unlock", "output_encode", "output_write", "recovery_notice"}
CODES = {"permission_denied", "file_missing", "timeout", "io_error", "encoding_error", "invalid_type",
         "missing_field", "invalid_data", "internal_error"}


def _key(key):
    if not isinstance(key, str) or not re.fullmatch(r"[a-f0-9]{24}", key):
        raise ValueError("recovery requires a valid session key")
    return key


def _records(root, key):
    directory = runtime_path(root, ".runtime/hook-errors")
    candidates = [(event, directory / f"{_key(key)}-{event}.json") for event in EVENTS]
    candidates.append(("StaticCheck", runtime_path(root, f".runtime/hook-checks/{key}.json")))
    result, unavailable = [], False
    for event, path in candidates:
        try:
            if not stat.S_ISREG(path.lstat().st_mode):
                raise ValueError("unsupported diagnostic path")
            with path.open("rb") as stream:
                raw = stream.read(8193)
            if len(raw) > 8192:
                raise ValueError("diagnostic exceeds limit")
            value = strict_json(raw.decode())
            stage, code = "diagnostic_read", "invalid_record"
            if event == "StaticCheck" and isinstance(value, dict) and value.get("version") == 1:
                if value.get("status") == "passed":
                    continue
                if value.get("status") in {"findings", "stale"}:
                    stage = "static_check"
                    code = "source_changed" if value["status"] == "stale" else "validation_findings"
            elif (isinstance(value, dict) and value.get("version") == 1
                  and value.get("status") == "callback_failed" and value.get("event") == event
                  and isinstance(value.get("stage"), str) and value["stage"] in STAGES
                  and isinstance(value.get("code"), str) and value["code"] in CODES):
                stage, code = value["stage"], value["code"]
            result.append({"event": event, "stage": stage, "code": code,
                           "path": path.relative_to(root).as_posix(),
                           "failure_sha256": hashlib.sha256(raw).hexdigest()})
        except FileNotFoundError:
            continue
        except (OSError, ValueError, TypeError, UnicodeError):
            unavailable = True
    return result, unavailable


def _receipt_path(root, key):
    return runtime_path(root, f".runtime/hook-receipts/{_key(key)}.json")


def _empty():
    return {"version": 1, "notified": {}, "resolved": {}}


def _receipt(root, key):
    path = _receipt_path(root, key)
    if not path.exists():
        return _empty()
    value = load(path, 16384)
    if (not isinstance(value, dict) or value.get("version") != 1
            or any(not isinstance(value.get(k), dict) or not set(value[k]).issubset(ISSUES)
                   for k in ("notified", "resolved"))
            or any(not isinstance(v, dict) for v in value["resolved"].values())):
        raise ValueError("invalid recovery receipt")
    return value


def _pending(records, receipt):
    return [r for r in records if receipt["resolved"].get(r["event"], {}).get("failure_sha256") != r["failure_sha256"]]


def status(root, key):
    try:
        records, unavailable = _records(root, key)
        if not records:
            return {"pending_failures": [], "recovery_unavailable": unavailable}
        try:
            receipt = _receipt(root, key)
        except (OSError, ValueError, TypeError):
            receipt, unavailable = _empty(), True
        return {"pending_failures": _pending(records, receipt), "recovery_unavailable": unavailable}
    except (OSError, ValueError, TypeError):
        return {"pending_failures": [], "recovery_unavailable": True}


def _notice(root, key, *, force=False):
    records, _ = _records(root, key)
    if not records:
        return ""
    from .hook_sessions import lock
    with lock(root, key) as acquired:
        if not acquired:
            return ""
        try:
            receipt = _receipt(root, key)
        except (OSError, ValueError, TypeError):
            receipt = _empty()
        selected = []
        for item in _pending(records, receipt):
            epoch = receipt["resolved"].get(item["event"], {}).get("failure_sha256")
            basis = (item["failure_sha256"] if item["event"] == "StaticCheck" else
                     [item["event"], item["stage"], item["code"], epoch])
            token = hashlib.sha256(json.dumps(basis).encode()).hexdigest()
            if force or receipt["notified"].get(item["event"]) != token:
                selected.append(item)
                receipt["notified"][item["event"]] = token
        if not selected:
            return ""
        try:
            atomic(_receipt_path(root, key), receipt)
        except (OSError, ValueError):
            pass  # Still deliver the notice; it may repeat until receipts can be saved.
    lines = ["미해결 훅 진단이 있다. hook status로 원문 위치·현재 해시를 읽고 원인/소유권/권한을 확인한다. 허용된 수정과 관련 재검증을 수행하고 실제 task 근거를 등록한 뒤 hook resolve로 해결을 기록한다. 차단/범위 밖은 task에 다음 행동을 남기며 미해결로 유지한다."]
    lines.extend(f"{r['event']}: stage={r['stage']} code={r['code']}; {r['path']}" for r in selected)
    return "\n".join(lines)


def merge(primary, extra):
    result = dict(primary)
    if extra.get("systemMessage"):
        result["systemMessage"] = " ".join(filter(None, (result.get("systemMessage"), extra["systemMessage"])))
    if extra.get("hookSpecificOutput"):
        value = dict(result.get("hookSpecificOutput", {}))
        incoming = extra["hookSpecificOutput"]
        value.setdefault("hookEventName", incoming["hookEventName"])
        if incoming.get("additionalContext"):
            value["additionalContext"] = "\n".join(filter(None, (value.get("additionalContext"), incoming["additionalContext"])))
        result["hookSpecificOutput"] = value
    return result


def attach(root, event, result):
    # Auxiliary feedback cannot weaken a deny or turn a successful tool into an error.
    try:
        name = event.get("hook_event_name")
        if name not in {"PreToolUse", "PostToolUse", "SessionStart", "Stop"}:
            return result
        from .hook_sessions import session_key
        notice = _notice(root, session_key(event.get("session_id")), force=name in {"SessionStart", "Stop"})
        if not notice:
            return result
        extra = ({"systemMessage": notice} if name == "Stop" else
                 {"hookSpecificOutput": {"hookEventName": name, "additionalContext": notice}})
        return merge(result, extra)
    except Exception:
        return result


def resolve(root, key, event, failure_sha256, task, ident):
    from . import evidence
    from .hook_sessions import lock
    if event not in ISSUES or not re.fullmatch(r"[a-f0-9]{64}", failure_sha256):
        raise ValueError("resolve requires an issue and the current diagnostic hash")
    path = evidence.task_file(root, task)
    data = load(path, 128000)
    entries = data.get("evidence") if isinstance(data, dict) else None
    entry = entries.get(ident) if isinstance(entries, dict) else None
    if not isinstance(entry, dict) or entry.get("type") not in {"artifact", "check"}:
        raise ValueError("resolve requires registered verification evidence")
    evidence.verify_entry(root, entry, path)
    with lock(root, key) as acquired:
        if not acquired:
            raise ValueError("recovery state is busy; retry after the current callback")
        records, _ = _records(root, key)
        current = next((r for r in records if r["event"] == event), None)
        if current is None or current["failure_sha256"] != failure_sha256:
            raise ValueError("diagnostic changed; inspect the current failure before resolving")
        if entry["path"] == current["path"] or entry["sha256"] == failure_sha256:
            raise ValueError("the failure record itself is not repair verification evidence")
        receipt = _receipt(root, key)
        receipt["resolved"][event] = {"failure_sha256": failure_sha256, "task": task, "evidence": ident,
                                     "evidence_sha256": entry["sha256"], "at": now()}
        atomic(_receipt_path(root, key), receipt)
    return {"status": "passed", "event": event, "resolution": "recorded", "task": task, "evidence": ident,
            "note": "Evidence integrity checked; the agent must judge whether it verifies this failure's repair."}
