"""Prompt submission adapter: prepare once, hand off execution through the host's tools.

Hooks cannot change the host turn's model/effort. Do not run a privileged child
from a hook: the host executes the handoff under its existing permission policy.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shlex
import sys
import uuid

from .cli import parser
from .execution import INPUT_LIMIT, enqueue
from ..core import strict_json
from .inputs import read_regular_text


def transcript_context(path):
    if path is None:
        return []
    if not isinstance(path, str):
        raise ValueError("invalid transcript path")
    source = Path(path).resolve()
    home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))).resolve()
    if not any(source.is_relative_to(home / directory) for directory in ("sessions", "archived_sessions")):
        raise ValueError("unrecognized transcript location")
    messages = []
    for line in read_regular_text(source, 32 * 1024 * 1024).splitlines():
        item = strict_json(line)
        if not isinstance(item, dict):
            raise ValueError("invalid transcript item")
        if item.get("type") != "response_item":
            continue
        payload = item.get("payload", {})
        if not isinstance(payload, dict):
            raise ValueError("invalid transcript payload")
        if payload.get("type") != "message" or payload.get("role") not in ("user", "assistant"):
            continue
        content = payload.get("content", [])
        if not isinstance(content, list) or not all(isinstance(c, dict) for c in content):
            raise ValueError("invalid transcript content")
        text = "\n".join(c.get("text", "") for c in content if c.get("type") in ("input_text", "output_text"))
        if text:
            messages.append({"role": payload["role"], "text": text})
    if not messages:
        return []
    text = json.dumps(messages, ensure_ascii=False)
    if len(text.encode()) > INPUT_LIMIT:
        raise ValueError("conversation requires an explicit handoff")
    return [{"reference": "host_conversation", "text": text}]


def prompt_hook(root):
    try:
        root = root.resolve()
        raw = sys.stdin.read(INPUT_LIMIT + 1)
        if len(raw.encode()) > INPUT_LIMIT:
            raise ValueError("hook input too large")
        event = strict_json(raw)
        if not isinstance(event, dict):
            raise ValueError("invalid hook event")
        if event.get("hook_event_name") != "UserPromptSubmit":
            raise ValueError("unexpected hook event")
        cwd = Path(event["cwd"]).resolve()
        if not cwd.is_relative_to(root):
            raise ValueError("hook outside repository")
        identifier = os.environ.get("HARNESS_ROUTING_DECISION")
        if identifier:
            identifier = str(uuid.UUID(identifier))
            record = cwd / ".runtime" / "routing" / identifier / "run.json"
            value = strict_json(read_regular_text(record, INPUT_LIMIT))
            if (os.environ.get("HARNESS_ROUTING_ROOT") != str(cwd) or
                    value.get("decision_id") != identifier or value.get("status") != "running"):
                raise ValueError("invalid worker marker")
            context = "This worker is already routed. Complete the current request; do not reroute it."
        else:
            if not isinstance(event.get("prompt"), str):
                raise ValueError("missing prompt")
            args = parser().parse_args(["run", "--cwd", str(cwd), "--", event["prompt"]])
            history = transcript_context(event.get("transcript_path"))
            decision, identifier = enqueue(args, history)
            if identifier is None:
                print(json.dumps({"decision": "block", "reason":
                      "라우팅이 준비되지 않아 작업을 차단했습니다: " + decision["status"]}, ensure_ascii=False))
                return 0
            command = shlex.join([sys.executable, str(root / "tools/harness/run.py"), "run",
                                  "--cwd", str(cwd), "--request-id", identifier])
            selected = decision["selected"]
            context = (
                f"Mandatory routing completed: {selected['model']} / {selected['effort']}. "
                "Before research, analysis, editing or answering the user request, execute the following "
                "handoff with the host's shell tool under its current sandbox and approval policy. "
                "It consumes the prepared request once, executes the selected model, and returns its result. "
                "Do not solve the task in this host model, run it twice, or retry after execution failure. "
                "If the current host sandbox is read-only, add --sandbox read-only; if workspace-write, "
                "add --sandbox workspace-write. Never broaden permissions. "
                "Report the returned result and limits. If the host denies execution, report that denial.\n"
                + command
            )
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                                                 "additionalContext": context}}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError):
        # Always block on a preparation failure; a crash/exit 1 can fail open in hosts.
        print(json.dumps({"decision": "block", "reason":
              "자동 라우팅 준비에 실패했습니다. run/chat 진입점과 명시적 인수인계 자료를 사용하세요."}, ensure_ascii=False))
        return 0
