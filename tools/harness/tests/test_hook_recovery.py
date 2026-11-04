"""Recovery notifications are per session, bounded, and resolved with evidence."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from _support import SOURCE
from harness import cli, hook_recovery as recovery, hook_sessions as sessions, lifecycle_hooks as hooks, tasks
from harness.provenance import atomic, load, now, sha


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="hook-recovery-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.key = sessions.session_key("recovery-fixture")
        self.event = {"session_id": "recovery-fixture", "hook_event_name": "PreToolUse"}

    def failure(self, code="invalid_data"):
        relative = hooks._failure_record(self.root, self.event,
                                         {"stage": "remote_guard", "session_key": self.key}, code, time.monotonic())
        return self.root / relative

    def proof(self):
        task = tasks.create(self.root, "repair", "debug", "Verify original callback", ["Callback succeeds"])
        observed = hooks.handle(self.root, dict(self.event, tool_name="Bash", tool_input={"command": "pwd"}))
        proof = self.root / ".runtime/verification.json"
        atomic(proof, {"event": "PreToolUse", "status": "passed", "observed_output": observed})
        data = load(task)
        data["evidence"]["VERIFY"] = {"type": "artifact", "path": ".runtime/verification.json", "sha256": sha(proof),
                                       "description": "Observed successful callback for the original fixture", "recorded_at": now()}
        atomic(task, data)
        return proof

    def test_normal_calls_do_not_create_receipts_or_run_inspections(self):
        with patch("harness.doctor.inspect", side_effect=AssertionError("no extra checks")):
            self.assertEqual(recovery.attach(self.root, self.event, {}), {})
        self.assertFalse((self.root / ".runtime").exists())

    def test_sessions_and_unidentified_records_are_not_mixed(self):
        self.failure()
        atomic(self.root / ".runtime/hook-errors/unidentified-unknown.json", {"private": "unassigned"})
        other = dict(self.event, session_id="other-session")
        self.assertEqual(recovery.attach(self.root, other, {}), {})
        self.assertEqual(len(sessions.status(self.root, self.key)["pending_failures"]), 1)
        self.assertFalse(sessions.status(self.root, sessions.session_key("other-session"))["pending_failures"])

    def test_repeated_same_failure_is_quiet_until_resume_and_new_stage_is_not(self):
        self.failure()
        self.assertIn("hookSpecificOutput", recovery.attach(self.root, self.event, {}))
        self.failure()
        self.assertEqual(recovery.attach(self.root, self.event, {}), {})
        self.failure("permission_denied")
        self.assertIn("permission_denied", recovery.attach(self.root, self.event, {})["hookSpecificOutput"]["additionalContext"])

    def test_registered_proof_resolves_exact_failure_and_later_failure_reopens(self):
        self.failure()
        recovery.attach(self.root, self.event, {})
        issue = sessions.status(self.root, self.key)["pending_failures"][0]
        self.proof()
        result = sessions.resolve(self.root, "PreToolUse", issue["failure_sha256"], "repair", "VERIFY", self.key)
        self.assertEqual(result["status"], "passed")
        self.assertFalse(sessions.status(self.root, self.key)["pending_failures"])
        self.assertEqual(recovery.attach(self.root, dict(self.event, hook_event_name="SessionStart"), {}), {})
        self.failure()
        self.assertTrue(sessions.status(self.root, self.key)["pending_failures"])
        self.assertIn("hookSpecificOutput", recovery.attach(self.root, self.event, {}))

    def test_stale_diagnostic_and_changed_or_missing_proof_cannot_resolve(self):
        self.failure()
        original = recovery.status(self.root, self.key)["pending_failures"][0]["failure_sha256"]
        proof = self.proof()
        self.failure("io_error")
        with self.assertRaises(ValueError):
            sessions.resolve(self.root, "PreToolUse", original, "repair", "VERIFY", self.key)
        current = recovery.status(self.root, self.key)["pending_failures"][0]["failure_sha256"]
        proof.write_text("changed")
        with self.assertRaises(ValueError):
            sessions.resolve(self.root, "PreToolUse", current, "repair", "VERIFY", self.key)
        with self.assertRaises(ValueError):
            sessions.resolve(self.root, "PreToolUse", current, "repair", "MISSING", self.key)
        self.assertTrue(recovery.status(self.root, self.key)["pending_failures"])

    def test_notice_preserves_deny_and_receipt_errors_do_not_weaken_policy(self):
        self.failure()
        denial = {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                         "permissionDecisionReason": "existing policy"}}
        with patch("harness.hook_recovery.atomic", side_effect=PermissionError("private receipt error")):
            result = recovery.attach(self.root, self.event, denial)
        self.assertEqual(result["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("additionalContext", result["hookSpecificOutput"])
        self.assertNotIn("private receipt error", json.dumps(result))
        with patch("harness.hook_recovery._records", side_effect=RuntimeError("private read error")):
            self.assertEqual(recovery.attach(self.root, self.event, denial), denial)

    def test_busy_notification_is_deferred_without_losing_unresolved_failure(self):
        self.failure()
        with sessions.lock(self.root, self.key):
            self.assertEqual(recovery.attach(self.root, self.event, {}), {})
        self.assertIn("hookSpecificOutput", recovery.attach(self.root, self.event, {}))
        self.assertTrue(recovery.status(self.root, self.key)["pending_failures"])

    def test_corrupt_session_state_still_exposes_recovery_status(self):
        self.failure()
        path = sessions.state_path(self.root, self.key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("not-json")
        value = sessions.status(self.root, self.key)
        self.assertEqual(value["status"], "failed")
        self.assertFalse(value["state_available"])
        self.assertTrue(value["pending_failures"])
        self.assertIn("hookSpecificOutput", recovery.attach(self.root, self.event, {}))
        atomic(path, {"version": 1, "task": None, "validation": None})
        self.assertTrue(sessions.status(self.root, self.key)["pending_failures"])

    def test_arbitrary_record_fields_are_never_replayed(self):
        path = self.failure()
        data = load(path)
        data.update(stage="ignore-all-rules-private", code="exfiltrate-private", instructions="private payload")
        atomic(path, data)
        result = recovery.attach(self.root, self.event, {})
        self.assertIn("invalid_record", json.dumps(result))
        self.assertNotIn("private", json.dumps(result))
        receipt = self.root / f".runtime/hook-receipts/{self.key}.json"
        self.assertEqual(receipt.stat().st_mode & 0o777, 0o600)
        self.assertNotIn("private", receipt.read_text())
        atomic(receipt, {"version": 1, "notified": {}, "resolved": {"PreToolUse": []}})
        value = recovery.status(self.root, self.key)
        self.assertTrue(value["recovery_unavailable"])
        self.assertTrue(value["pending_failures"])

    def test_static_findings_are_pending_and_verified_static_pass_clears_them(self):
        path = self.root / f".runtime/hook-checks/{self.key}.json"
        atomic(path, {"version": 1, "status": "findings", "arbitrary": "private result"})
        result = recovery.attach(self.root, dict(self.event, hook_event_name="PostToolUse"), {})
        self.assertIn("StaticCheck", result["hookSpecificOutput"]["additionalContext"])
        self.assertNotIn("private result", json.dumps(result))
        self.assertEqual(recovery.status(self.root, self.key)["pending_failures"][0]["code"], "validation_findings")
        atomic(path, {"version": 1, "status": "passed"})
        self.assertFalse(recovery.status(self.root, self.key)["pending_failures"])
        atomic(path, {"version": 1, "status": "stale"})
        self.assertIn("source_changed", recovery.attach(self.root, self.event, {})["hookSpecificOutput"]["additionalContext"])

    def test_cli_status_and_resolve_use_real_registered_evidence(self):
        self.failure()
        self.proof()
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(cli.main(["hook", "status", "--session-key", self.key], root=self.root), 0)
        digest = json.loads(output.getvalue())["pending_failures"][0]["failure_sha256"]
        with redirect_stdout(io.StringIO()):
            code = cli.main(["hook", "resolve", "PreToolUse", "--session-key", self.key,
                             "--failure-sha256", digest, "--task", "repair", "--evidence", "VERIFY"], root=self.root)
        self.assertEqual(code, 0)
        self.assertFalse(recovery.status(self.root, self.key)["pending_failures"])

    def test_failure_record_cannot_be_its_own_verification_and_symlinks_are_not_read(self):
        failure = self.failure()
        self.proof()
        task = self.root / "docs/tasks/repair/task.json"
        data = load(task)
        data["evidence"]["VERIFY"].update(path=failure.relative_to(self.root).as_posix(), sha256=sha(failure))
        atomic(task, data)
        digest = recovery.status(self.root, self.key)["pending_failures"][0]["failure_sha256"]
        with self.assertRaises(ValueError):
            sessions.resolve(self.root, "PreToolUse", digest, "repair", "VERIFY", self.key)
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / "private.json"
            target.write_text('{"private":"never read"}')
            failure.unlink()
            failure.symlink_to(target)
            value = recovery.status(self.root, self.key)
            self.assertTrue(value["recovery_unavailable"])
            self.assertFalse(value["pending_failures"])


if __name__ == "__main__":
    unittest.main()
