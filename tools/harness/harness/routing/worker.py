"""One bounded Codex process; argv is explicit and task material travels on stdin."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import threading
import time
import uuid

from ..core import strict_json
from ..processes import _stop
from .inputs import read_regular_text


def worker_command(executable, cwd, selected, output, sandbox=None):
    command = [executable, "exec", "--strict-config", "-C", str(cwd),
               "--model", selected["model"], "-c",
               "model_reasoning_effort=" + json.dumps(selected["effort"]),
               "--json", "--color", "never", "--output-last-message", str(output)]
    if sandbox is not None:
        command.extend(["--sandbox", sandbox])
    # Do not override auth, approvals, rules, tools, hooks, provider, or user config.
    command.append("-")
    return command


def observe_configuration(thread_id, cwd):
    """Read only this newly launched thread's local configuration, never infer it."""
    if not thread_id:
        return None
    home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    try:
        files = list((home / "sessions").glob(f"**/rollout-*{thread_id}.jsonl"))
        if len(files) != 1:
            return None
        observed = None
        for line in read_regular_text(files[0], 32 * 1024 * 1024).splitlines():
            item = strict_json(line)
            if not isinstance(item, dict):
                raise ValueError("invalid rollout record")
            if item.get("type") != "turn_context":
                continue
            value = item.get("payload", {})
            if not isinstance(value, dict):
                raise ValueError("invalid turn context")
            if Path(value.get("cwd", "")).resolve() != cwd:
                continue
            model, effort = value.get("model"), value.get("effort")
            if isinstance(model, str) and isinstance(effort, str):
                observed = {"model": model, "effort": effort,
                            "source": "codex_turn_context"}
        return observed
    except (OSError, ValueError, TypeError):
        return None


def execute_worker(executable, cwd, selected, prompt, decision_id, *, timeout,
                   max_output_bytes, sandbox=None):
    started = time.monotonic()
    result = {"task_executed": False, "worker_started": False, "exit_code": None, "error": None,
              "thread_id": None, "usage": None, "observed_configuration": None,
              "response": "", "duration_seconds": 0}
    env = dict(os.environ, HARNESS_ROUTING_DECISION=decision_id,
               HARNESS_ROUTING_ROOT=str(cwd))
    with tempfile.TemporaryDirectory(prefix="harness-worker-") as name:
        output = Path(name) / "response.txt"
        command = worker_command(executable, cwd, selected, output, sandbox)
        try:
            process = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       start_new_session=os.name == "posix")
        except OSError:
            result["error"] = "cannot_execute"
            return result
        result["worker_started"] = True
        stopped = threading.Event()
        problem = []
        total = [0]
        counter_lock = threading.Lock()
        completed = [False]
        diagnostics = bytearray()

        def fail(reason):
            problem.append(reason)
            stopped.set()

        def event(line):
            try:
                value = strict_json(line)
                if not isinstance(value, dict) or not isinstance(value.get("type"), str):
                    raise ValueError
                kind = value["type"]
                if kind == "turn.started":
                    result["task_executed"] = True
                if kind in ("error", "turn.failed"):
                    fail("worker_reported_failure")
                if kind == "thread.started":
                    identifier = str(uuid.UUID(value["thread_id"]))
                    if result["thread_id"] not in (None, identifier):
                        raise ValueError
                    result["thread_id"] = identifier
                if kind == "turn.completed":
                    if completed[0]:
                        raise ValueError
                    completed[0] = True
                    usage = value.get("usage")
                    keys = ("input_tokens", "cached_input_tokens", "output_tokens",
                            "reasoning_output_tokens")
                    if isinstance(usage, dict) and all(type(usage.get(k, 0)) is int and
                                                      usage.get(k, 0) >= 0 for k in keys):
                        result["usage"] = {k: usage[k] for k in keys if k in usage}
            except (ValueError, TypeError, KeyError, UnicodeError):
                fail("invalid_worker_events")

        def drain(pipe, parse=False):
            buffer = b""
            try:
                while block := os.read(pipe.fileno(), 65536):
                    with counter_lock:
                        total[0] += len(block)
                        overflow = total[0] > max_output_bytes
                    if overflow:
                        fail("output_limit")
                        return
                    if not parse and len(diagnostics) < 4096:
                        diagnostics.extend(block[:4096-len(diagnostics)])
                    if parse:
                        buffer += block
                        while b"\n" in buffer:
                            line, buffer = buffer.split(b"\n", 1)
                            if len(line) > 1024 * 1024:
                                fail("event_line_limit")
                                return
                            if line.strip():
                                event(line)
                        if len(buffer) > 1024 * 1024:
                            fail("event_line_limit")
                            return
                if parse and buffer.strip():
                    event(buffer)
            except (OSError, ValueError):
                fail("output_read_error")

        def feed():
            try:
                process.stdin.write(prompt.encode("utf-8"))
                process.stdin.close()
            except (OSError, ValueError):
                fail("input_write_error")

        threads = [threading.Thread(target=drain, args=(process.stdout, True), daemon=True),
                   threading.Thread(target=drain, args=(process.stderr,), daemon=True),
                   threading.Thread(target=feed, daemon=True)]
        for thread in threads:
            thread.start()
        try:
            while process.poll() is None or any(t.is_alive() for t in threads):
                if stopped.wait(0.02):
                    result["error"] = problem[0]
                    break
                if time.monotonic() - started >= timeout:
                    result["error"] = "timeout"
                    break
        except KeyboardInterrupt:
            result["error"] = "interrupted"
        finally:
            cleanup_error = _stop(process)
            if cleanup_error:
                result["cleanup_error"] = cleanup_error
                result["error"] = result["error"] or cleanup_error
            result["exit_code"] = process.wait(timeout=5)
            for thread in threads:
                thread.join(timeout=2)
            if any(t.is_alive() for t in threads):
                result["error"] = result["error"] or "stream_cleanup_failed"
            else:
                for pipe in (process.stdin, process.stdout, process.stderr):
                    pipe.close()
        result["error"] = result["error"] or (problem[0] if problem else None)
        if result["exit_code"] and not result["error"]:
            result["error"] = "worker_exit_failure"
            if b"failed to initialize in-process app-server client: Operation not permitted" in diagnostics:
                result["error"] = "startup_permission_denied"
        if not completed[0] and not result["error"]:
            result["error"] = "worker_incomplete"
        if completed[0] and (not result["thread_id"] or not result["task_executed"]) and not result["error"]:
            result["error"] = "invalid_worker_lifecycle"
        try:
            if output.exists():
                result["response"] = read_regular_text(output, max_output_bytes)
        except (OSError, ValueError):
            result["error"] = result["error"] or "response_read_error"
        if not result["response"].strip() and not result["error"]:
            result["error"] = "missing_response"
        result["observed_configuration"] = observe_configuration(result["thread_id"], cwd)
        observed = result["observed_configuration"]
        if observed and any(observed[k] != selected[k] for k in ("model", "effort")):
            result["error"] = "configuration_mismatch"
    result["duration_seconds"] = round(time.monotonic() - started, 3)
    return result
