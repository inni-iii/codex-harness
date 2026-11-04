"""Lifecycle behavior uses local metadata and never sends remote commands."""
from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from _support import SOURCE
from harness import cli, hook_sessions as sessions, lifecycle_hooks as hooks, remote_guard, tasks
from harness.provenance import atomic, load


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="lifecycle-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        config = self.root / "tools/harness/harness.toml"
        config.parent.mkdir(parents=True)
        config.write_text('version=1\n')
        (self.root / "README.md").write_text("# Fixture\n")
        self.key = sessions.session_key("fixture-session")

    def event(self, name, **fields):
        return {"hook_event_name": name, "session_id": "fixture-session", "cwd": str(self.root), **fields}

    def task(self, slug="current"):
        return tasks.create(self.root, slug, "implement", "Local task", ["Observable result"])

    def invoke(self, payload):
        raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        output, error = io.StringIO(), io.StringIO()
        with patch.object(sys, "stdin", io.TextIOWrapper(io.BytesIO(raw))), redirect_stdout(output), redirect_stderr(error):
            code = hooks.main(self.root)
        return code, output.getvalue(), error.getvalue()

    def test_callback_failure_records_safe_stage_code_and_elapsed_time(self):
        private = "private-response-and-exception-body"
        event = self.event("PostToolUse", tool_name="Bash", tool_response=private)
        with patch("harness.doctor.inspect", side_effect=PermissionError(private)):
            code, output, error = self.invoke(event)
        self.assertEqual(code, 1)
        self.assertEqual(output, "")
        path = self.root / f".runtime/hook-errors/{self.key}-PostToolUse.json"
        record = json.loads(path.read_text())
        self.assertEqual(record["stage"], "doctor")
        self.assertEqual(record["code"], "permission_denied")
        self.assertEqual(record["status"], "callback_failed")
        self.assertGreaterEqual(record["elapsed_ms"], 0)
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertIn("stage=doctor", error)
        self.assertLess(len(error), 250)
        self.assertNotIn(private, path.read_text() + output + error)
        self.assertNotIn("fixture-session", path.read_text())

    def test_parse_failures_use_fixed_unidentified_record_without_input_echo(self):
        for payload, stage in ((b'{"private-query":', "input_parse"),
                               (b'\xff', "input_decode"),
                               (b'x' * (hooks.INPUT_LIMIT + 1), "input_limit")):
            with self.subTest(stage=stage):
                code, output, error = self.invoke(payload)
                self.assertEqual(code, 1)
                record = load(self.root / ".runtime/hook-errors/unidentified-unknown.json")
                self.assertEqual(record["stage"], stage)
                self.assertNotIn("private-query", json.dumps(record) + output + error)
        self.assertEqual(len(list((self.root / ".runtime/hook-errors").glob("*.json"))), 1)

    def test_state_save_and_unexpected_failure_remain_nonzero_and_sanitized(self):
        private = "private-state-path-or-runtime-error"
        with patch("harness.hook_sessions.save", side_effect=OSError(private)):
            code, output, error = self.invoke(self.event("SessionStart", source="startup"))
        record = load(self.root / f".runtime/hook-errors/{self.key}-SessionStart.json")
        self.assertEqual((code, record["stage"], record["code"]), (1, "state_write", "io_error"))
        with patch("harness.remote_guard.inspect", side_effect=RuntimeError(private)):
            code, output, error = self.invoke(self.event("PreToolUse", tool_name="Bash", tool_input={"command": "pwd"}))
        record = load(self.root / f".runtime/hook-errors/{self.key}-PreToolUse.json")
        self.assertEqual((code, record["stage"], record["code"]), (1, "remote_guard", "internal_error"))
        self.assertNotIn(private, json.dumps(record) + output + error)

    def test_diagnostic_write_failure_keeps_original_failure_and_short_summary(self):
        with patch("harness.remote_guard.inspect", side_effect=ValueError("private cause")), patch(
                "harness.lifecycle_hooks.atomic", side_effect=PermissionError("private logger failure")):
            code, output, error = self.invoke(self.event("PreToolUse", tool_name="Bash", tool_input={"command": "pwd"}))
        self.assertEqual(code, 1)
        self.assertEqual(output, "")
        self.assertIn("stage=remote_guard", error)
        self.assertIn("diagnostic_unavailable", error)
        self.assertNotIn("private", error)

    def test_success_preserves_output_and_adds_no_failure_files_or_checks(self):
        with patch("harness.lifecycle_hooks._inventory", side_effect=AssertionError("no scan for shell pre-hook")):
            code, output, error = self.invoke(self.event("PreToolUse", tool_name="Bash", tool_input={"command": "pwd"}))
        self.assertEqual((code, output, error), (0, "{}\n", ""))
        self.assertFalse((self.root / ".runtime/hook-errors").exists())
        hooks.handle(self.root, self.event("SessionStart", source="startup"))
        with patch("harness.doctor.inspect", return_value={"status": "passed", "errors": []}) as doctor:
            (self.root / "README.md").write_text("# One update\n")
            self.assertEqual(hooks.handle(self.root, self.event("PostToolUse", tool_name="Bash")), {})
            self.assertEqual(hooks.handle(self.root, self.event("PostToolUse", tool_name="Bash")), {})
            doctor.assert_called_once()
        self.assertFalse((self.root / ".runtime/hook-errors").exists())

    def test_static_findings_and_stale_have_safe_distinct_reasons(self):
        hooks.handle(self.root, self.event("SessionStart", source="startup"))
        (self.root / "README.md").write_text("# Changed\n")
        private = "private-link-or-diagnostic"
        with patch("harness.doctor.inspect", return_value={"status": "failed", "errors": ["broken/outside link in " + private]}):
            output = hooks.handle(self.root, self.event("PostToolUse", tool_name="Bash"))
        report = self.root / f".runtime/hook-checks/{self.key}.json"
        result = load(report)
        self.assertEqual(result["status"], "findings")
        self.assertIn("document_link", result["results"]["doctor"]["reason_codes"])
        self.assertGreaterEqual(result["elapsed_ms"], 0)
        self.assertIn("findings", output["systemMessage"])
        self.assertNotIn(private, report.read_text() + json.dumps(output))
        (self.root / "README.md").write_text("# Next change\n")
        def race(_):
            (self.root / "README.md").write_text("# Changed during inspection\n")
            return {"status": "passed", "errors": []}
        with patch("harness.doctor.inspect", side_effect=race):
            output = hooks.handle(self.root, self.event("PostToolUse", tool_name="Bash"))
        self.assertEqual(load(report)["reason_codes"], ["source_changed"])
        self.assertIn("stale", output["systemMessage"])
        self.assertFalse((self.root / ".runtime/hook-errors").exists())

    def test_binding_is_explicit_private_and_current_session_only(self):
        self.task()
        self.assertIsNone(sessions.status(self.root, self.key)["task"])
        sessions.bind(self.root, "current", self.key)
        self.assertEqual(sessions.status(self.root, self.key)["task"], "current")
        self.assertIsNone(sessions.status(self.root, sessions.session_key("other"))["task"])
        path = sessions.state_path(self.root, self.key)
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertNotIn("fixture-session", path.read_text())
        sessions.clear(self.root, self.key)
        self.assertIsNone(sessions.status(self.root, self.key)["task"])

    def test_cli_uses_thread_environment_or_explicit_key_without_model_calls(self):
        self.task()
        for arguments in (["hook", "bind", "current"], ["hook", "status"], ["hook", "clear"]):
            output = io.StringIO()
            with patch.dict(os.environ, {"CODEX_THREAD_ID": "fixture-session"}), redirect_stdout(output):
                self.assertEqual(cli.main(arguments, root=self.root), 0)
            self.assertEqual(json.loads(output.getvalue())["session_key"], self.key)

    def test_bad_binding_paths_keys_and_runtime_symlinks_do_not_write_outside(self):
        self.task()
        for slug in ("../other", "absent"):
            with self.assertRaises(ValueError):
                sessions.bind(self.root, slug, self.key)
        with self.assertRaises(ValueError):
            sessions.status(self.root, "../escape")
        with tempfile.TemporaryDirectory() as outside:
            runtime = self.root / ".runtime"
            if runtime.exists():
                runtime.rmdir()  # Task map locking may leave an empty runtime directory.
            runtime.symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                sessions.bind(self.root, "current", self.key)
            self.assertFalse(list(Path(outside).iterdir()))

    def test_stop_ignores_unbound_tasks_and_warns_once_for_bound_task(self):
        self.task("unrelated")
        self.assertEqual(hooks.handle(self.root, self.event("Stop")), {})
        self.task()
        sessions.bind(self.root, "current", self.key)
        result = hooks.handle(self.root, self.event("Stop"))
        self.assertIn("current", result["systemMessage"])
        self.assertNotIn("unrelated", result["systemMessage"])
        self.assertNotIn("decision", result)
        self.assertEqual(hooks.handle(self.root, self.event("Stop", stop_hook_active=True)), {})
        (self.root / "app.py").write_text("# Changed product source\n")
        self.assertIn("systemMessage", hooks.handle(self.root, self.event("Stop")))

    def test_stop_uses_existing_assessment_and_does_not_complete_or_run_tests(self):
        self.task()
        sessions.bind(self.root, "current", self.key)
        with patch("harness.evidence.assess", return_value=[]) as assess:
            self.assertEqual(hooks.handle(self.root, self.event("Stop")), {})
            self.assertEqual(hooks.handle(self.root, self.event("Stop")), {})
            self.assertEqual(assess.call_count, 2)
        self.assertEqual(load(self.root / "docs/tasks/current/task.json")["status"], "planned")

    def test_stop_releases_finished_binding_and_missing_handoff_is_advisory(self):
        path = self.task()
        sessions.bind(self.root, "current", self.key)
        (path.parent / "notes.md").unlink()
        with patch("harness.evidence.assess", return_value=[]):
            self.assertIn("인수인계", hooks.handle(self.root, self.event("Stop"))["systemMessage"])
        data = load(path)
        data["status"] = "complete"
        atomic(path, data)
        self.assertEqual(hooks.handle(self.root, self.event("Stop")), {})
        self.assertIsNone(sessions.status(self.root, self.key)["task"])

    def test_stop_notices_changed_runtime_evidence_even_without_source_edits(self):
        self.task()
        sessions.bind(self.root, "current", self.key)
        with patch("harness.evidence.assess", side_effect=[[], ["registered runtime evidence changed"]]):
            self.assertEqual(hooks.handle(self.root, self.event("Stop")), {})
            proof = self.root / ".runtime/external-proof.json"
            proof.write_text('{"status":"failed"}')
            self.assertIn("systemMessage", hooks.handle(self.root, self.event("Stop")))

    def test_interrupt_is_metadata_only_and_resume_links_the_checkpoint(self):
        self.task()
        sessions.bind(self.root, "current", self.key)
        payload = "never-copy-conversation-or-tool-response"
        with patch("harness.lifecycle_hooks._inventory", side_effect=AssertionError("interrupt must not scan source")):
            self.assertEqual(hooks.handle(self.root, self.event("Interrupt", prompt=payload, tool_response=payload)), {})
        path = self.root / f".runtime/knowledge-events/{self.key}-Interrupt.json"
        text = path.read_text()
        self.assertNotIn(payload, text)
        self.assertNotIn("fixture-session", text)
        self.assertEqual(json.loads(text)["tasks"][0]["path"], "docs/tasks/current/task.json")
        output = hooks.handle(self.root, self.event("SessionStart", source="resume"))
        context = output["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Interrupt.json", context)
        self.assertIn(self.key, context)
        self.assertIn("current", context)

    def test_post_tool_checks_scoped_changes_once_and_leaves_application_tests_alone(self):
        hooks.handle(self.root, self.event("SessionStart", source="startup"))
        with patch("harness.doctor.inspect", return_value={"status": "passed", "errors": []}) as doctor, patch(
                "harness.agent_config.inspect", return_value={"status": "passed", "findings": []}) as config:
            (self.root / "app.py").write_text("# unrelated product source\n")
            hooks.handle(self.root, self.event("PostToolUse", tool_name="Bash"))
            doctor.assert_not_called()
            (self.root / "README.md").write_text("# Changed docs\n")
            self.assertEqual(hooks.handle(self.root, self.event("PostToolUse", tool_name="apply_patch")), {})
            hooks.handle(self.root, self.event("PostToolUse", tool_name="Bash"))
            self.assertEqual(doctor.call_count, 1)
            config.assert_not_called()
            path = self.root / ".codex/hooks.json"
            path.parent.mkdir()
            path.write_text('{"hooks":{}}')
            hooks.handle(self.root, self.event("PostToolUse", tool_name="apply_patch"))
            self.assertEqual(doctor.call_count, 2)
            self.assertEqual(config.call_count, 1)
        state = sessions.read(self.root, self.key)
        self.assertEqual(state["validation"]["checks"], ["doctor", "agent-config"])

    def test_static_findings_are_sanitized_and_source_races_are_not_cached_as_passes(self):
        private = "do-not-forward-raw-diagnostic-or-key"
        with patch("harness.doctor.inspect", return_value={"status": "failed", "errors": [private]}), patch(
                "harness.agent_config.inspect", return_value={"status": "passed", "findings": []}):
            output = hooks.handle(self.root, self.event("PostToolUse", tool_name="Bash", tool_response=private))
        self.assertIn("systemMessage", output)
        report = self.root / f".runtime/hook-checks/{self.key}.json"
        self.assertNotIn(private, report.read_text() + json.dumps(output))
        self.assertEqual(json.loads(report.read_text())["status"], "findings")
        def change(_):
            (self.root / "README.md").write_text("# Concurrent modification\n")
            return {"status": "passed", "errors": []}
        (self.root / "README.md").write_text("# Changed again\n")
        with patch("harness.doctor.inspect", side_effect=change):
            hooks.handle(self.root, self.event("PostToolUse", tool_name="apply_patch"))
        self.assertEqual(load(report)["status"], "stale")

    def test_busy_callbacks_do_not_wait_or_reenter_and_unrecognized_tools_do_nothing(self):
        with sessions.lock(self.root, self.key) as acquired:
            self.assertTrue(acquired)
            self.assertEqual(hooks.handle(self.root, self.event("Interrupt")), {})
        self.assertEqual(hooks.handle(self.root, self.event("PostToolUse", tool_name="WebSearch")), {})

    def test_mcp_pre_and_post_return_context_without_shell_parsing_or_payload_echo(self):
        private = "private-input-and-fake-system-instruction"
        name = "mcp__docs_server__search_docs"
        with patch("harness.remote_guard.inspect", side_effect=AssertionError("MCP is not shell input")):
            pre = hooks.handle(self.root, self.event("PreToolUse", tool_name=name,
                                tool_input={"query": private}))
            post = hooks.handle(self.root, self.event("PostToolUse", tool_name=name,
                                 tool_response={"content": [{"type": "text", "text": private}]}))
        for event, value in (("PreToolUse", pre), ("PostToolUse", post)):
            output = value["hookSpecificOutput"]
            self.assertEqual(output["hookEventName"], event)
            self.assertTrue(output["additionalContext"])
            self.assertNotIn("permissionDecision", output)
            self.assertNotIn("decision", value)
            self.assertNotIn(private, json.dumps(value))
        for path in (self.root / ".runtime").rglob("*.json"):
            self.assertNotIn(private, path.read_text())

    def test_mcp_response_error_or_missing_output_is_visible_without_blocking(self):
        for response in ({"isError": True, "content": [{"type": "text", "text": "private error"}]},
                         {"isError": "false"}, None):
            with self.subTest(response=response):
                value = hooks.handle(self.root, self.event("PostToolUse",
                                     tool_name="mcp__docs__search", tool_response=response))
                self.assertIn("systemMessage", value)
                self.assertNotIn("private error", json.dumps(value))
                self.assertNotIn("decision", value)
        valid = hooks.handle(self.root, self.event("PostToolUse", tool_name="mcp__docs__search",
                             tool_response={"isError": False, "structuredContent": {"count": 1}}))
        self.assertNotIn("systemMessage", valid)

    def test_mcp_local_file_changes_receive_existing_static_checks(self):
        hooks.handle(self.root, self.event("SessionStart", source="startup"))
        name = "mcp__filesystem__write_file"
        with patch("harness.doctor.inspect", return_value={"status": "passed", "errors": []}) as doctor:
            hooks.handle(self.root, self.event("PostToolUse", tool_name=name, tool_response={}))
            doctor.assert_not_called()
            (self.root / "README.md").write_text("# MCP changed watched documentation\n")
            output = hooks.handle(self.root, self.event("PostToolUse", tool_name=name, tool_response={}))
            self.assertIn("hookSpecificOutput", output)
            doctor.assert_called_once()
            hooks.handle(self.root, self.event("PostToolUse", tool_name=name, tool_response={}))
            doctor.assert_called_once()

    def test_mcp_advisory_survives_busy_static_checker_and_ignores_hosted_tools(self):
        with sessions.lock(self.root, self.key):
            output = hooks.handle(self.root, self.event("PostToolUse", tool_name="mcp__docs__search",
                                  tool_response={"isError": True}))
            self.assertEqual(output["hookSpecificOutput"]["hookEventName"], "PostToolUse")
            self.assertIn("systemMessage", output)
        for name in ("WebSearch", "web.run", "web__run", "mcp__incomplete", "mcp____search", "mcp__x__search\n"):
            self.assertEqual(hooks.handle(self.root, self.event("PreToolUse", tool_name=name)), {})
            self.assertEqual(hooks.handle(self.root, self.event("PostToolUse", tool_name=name)), {})

    def test_mcp_error_and_static_findings_are_both_retained(self):
        hooks.handle(self.root, self.event("SessionStart", source="startup"))
        (self.root / "README.md").write_text("# Changed through MCP\n")
        with patch("harness.doctor.inspect", return_value={"status": "failed", "errors": ["private diagnostic"]}):
            result = hooks.handle(self.root, self.event("PostToolUse", tool_name="mcp__files__write",
                                  tool_response={"isError": True}))
        self.assertIn("MCP", result["systemMessage"])
        self.assertIn(".runtime/hook-checks/", result["systemMessage"])
        self.assertNotIn("private diagnostic", json.dumps(result))

    def test_registered_mcp_matchers_and_real_stdin_events_agree(self):
        definition = json.loads((SOURCE / ".codex/hooks.json").read_text())["hooks"]
        name = "mcp__docs_server__search_docs"
        for event in ("PreToolUse", "PostToolUse"):
            self.assertTrue(any(re.fullmatch(group["matcher"], name) for group in definition[event]))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            shutil.copytree(SOURCE / "tools/harness", root / "tools/harness", ignore=shutil.ignore_patterns("__pycache__"))
            for event in ("PreToolUse", "PostToolUse"):
                payload = {"session_id": "stdin-mcp-fixture", "hook_event_name": event, "tool_name": name,
                           "tool_input": {"query": "private-payload"}, "tool_response": {"isError": True}}
                result = subprocess.run([sys.executable, str(root / "tools/harness/scripts/knowledge-hook.py")],
                                        input=json.dumps(payload), capture_output=True, text=True, timeout=5)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)["hookSpecificOutput"]["hookEventName"], event)
                self.assertNotIn("private-payload", result.stdout + result.stderr)

    def test_interrupt_still_records_while_another_callback_owns_the_state_lock(self):
        self.task()
        sessions.bind(self.root, "current", self.key)
        with sessions.lock(self.root, self.key):
            self.assertEqual(hooks.handle(self.root, self.event("Interrupt")), {})
        path = self.root / f".runtime/knowledge-events/{self.key}-Interrupt.json"
        self.assertTrue(path.is_file())
        self.assertEqual(load(path)["tasks"][0]["path"], "docs/tasks/current/task.json")

    def test_malformed_bound_task_is_a_bounded_warning_not_a_callback_traceback(self):
        path = self.task()
        sessions.bind(self.root, "current", self.key)
        path.write_text('[]')
        self.assertIn("systemMessage", hooks.handle(self.root, self.event("Stop")))

    def test_real_stdin_entrypoint_and_config_contract_preserve_router_removal(self):
        shutil.copytree(SOURCE / "tools/harness/harness", self.root / "tools/harness/harness", dirs_exist_ok=True)
        script = self.root / "tools/harness/scripts/knowledge-hook.py"
        script.parent.mkdir()
        shutil.copyfile(SOURCE / "tools/harness/scripts/knowledge-hook.py", script)
        self.task()
        sessions.bind(self.root, "current", self.key)
        for event in (self.event("Interrupt"), self.event("PreToolUse", tool_name="Bash", tool_input={"command": "scp local host:/target"})):
            result = subprocess.run([sys.executable, str(script)], input=json.dumps(event), capture_output=True, text=True, timeout=3)
            self.assertEqual(result.returncode, 0, result.stderr)
            output = json.loads(result.stdout)
            if event["hook_event_name"] == "PreToolUse":
                self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny")
        invalid = subprocess.run([sys.executable, str(script)], input="x" * (hooks.INPUT_LIMIT + 1), capture_output=True, text=True, timeout=3)
        self.assertNotEqual(invalid.returncode, 0)
        self.assertNotIn("x" * 100, invalid.stdout + invalid.stderr)
        config = json.loads((SOURCE / ".codex/hooks.json").read_text())
        self.assertEqual(set(config["hooks"]), hooks.EVENTS)
        self.assertNotIn("UserPromptSubmit", config["hooks"])
        self.assertLessEqual(config["hooks"]["Interrupt"][0]["hooks"][0]["timeout"], 3)


class RemoteGuardTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()

    def test_direct_writes_uploads_wrappers_and_remote_service_changes_are_denied(self):
        commands = ["ssh host 'touch /tmp/file'", "ssh -p 2222 host 'git fetch origin'",
                    "ssh host 'sed -i.bak s/a/b/ file'", "ssh host 'echo data > /tmp/file'",
                    "ssh host 'sudo systemctl restart app'", "ssh host 'uv sync --locked'",
                    "scp -i identity local host:/destination", "scp first:/source second:/destination",
                    "rsync -av --exclude '*.log' local/ host:/destination/", "rsync --remove-source-files host:/source ./local",
                    "bash -lc 'scp local host:/target'", "env MODE=inspect ssh host 'rm /tmp/file'",
                    "ssh host 'cat file; mkdir /tmp/created'", "ssh -R 9000:localhost:9000 host"]
        for command in commands:
            with self.subTest(command=command):
                self.assertIsNotNone(remote_guard.inspect(self.root, command))
        event = {"hook_event_name": "PreToolUse", "session_id": "fixture", "tool_name": "Bash", "tool_input": {"command": commands[0]}}
        output = hooks.handle(self.root, event)
        self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertNotIn(commands[0], json.dumps(output))
        self.assertFalse((self.root / ".runtime").exists())

    def test_reads_downloads_local_commands_and_quoted_examples_are_not_denied(self):
        commands = ["ssh host 'cat /etc/os-release'", "ssh -p2222 host 'git log -1'", "ssh host 'ls -l /var/log'",
                    "ssh host 'cat missing 2>/dev/null'", "ssh host \"printf '%s' '>'\"",
                    "scp -P 2222 host:/source ./local", "rsync -av host:/source ./local/",
                    "rm local-file", "printf '%s' 'ssh host rm /tmp/example'", "git status --short",
                    "ssh host 'echo readable # rm /tmp/not-a-command'", "ssh host 'git branch --show-current'"]
        for command in commands:
            with self.subTest(command=command):
                self.assertIsNone(remote_guard.inspect(self.root, command))

    def test_sftp_batch_is_read_only_and_does_not_follow_external_paths(self):
        path = self.root / "batch.txt"
        path.write_text("get /remote ./local\nls\n")
        self.assertIsNone(remote_guard.inspect(self.root, "sftp -b batch.txt host"))
        path.write_text("put ./local /remote\n")
        self.assertEqual(remote_guard.inspect(self.root, "sftp -b batch.txt host"), "sftp-batch-write")
        self.assertIsNone(remote_guard.inspect(self.root, "sftp -b /outside/private host"))

    def test_attached_ssh_remotecommand_and_rsync_server_prefix_writes_are_denied(self):
        for command in ("ssh -oRemoteCommand='touch /tmp/file' host",
                        "rsync --rsync-path='mkdir -p /tmp/cache; rsync' host:/source ./local",
                        "ssh > ./copy host 'touch /tmp/file'"):
            with self.subTest(command=command):
                self.assertIsNotNone(remote_guard.inspect(self.root, command))
        path = self.root / "batch.txt"
        path.write_text("  -put ./local /remote\n")
        self.assertEqual(remote_guard.inspect(self.root, "sftp -bbatch.txt host"), "sftp-batch-write")

    def test_local_output_redirection_does_not_turn_ssh_reads_into_remote_writes(self):
        for command in ("ssh host cat /etc/os-release > ./copy", "ssh > ./copy host 'cat /etc/os-release'",
                        "ssh host 'cat /etc/os-release' 2> ./errors > ./copy"):
            with self.subTest(command=command):
                self.assertIsNone(remote_guard.inspect(self.root, command))


if __name__ == "__main__":
    unittest.main()
