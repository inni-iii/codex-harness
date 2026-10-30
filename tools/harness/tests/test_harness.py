"""Behavioral tests for verification honesty, scoping and reproducibility."""
from __future__ import annotations

import io
from contextlib import redirect_stdout
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from _support import SOURCE

from harness import checks, doctor, tasks
from harness.cli import main, setup
from harness.core import fingerprint, source_paths
from harness.mcp import decode, probe



class Workspace(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="harness-test-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.config()

    def config(self, command=None, summary="", patterns=None):
        command = command or ["{python}", "probe.py"]
        data = 'version = 1\n[stack]\nfrontend = "svelte"\nbackend = "python"\n'
        data += '[[checks]]\nid = "unit"\ncommand = ' + json.dumps(command) + '\n'
        data += 'paths = ' + json.dumps(patterns or ["src/**", "probe.py"]) + '\ncacheable = true\ntimeout = 10\n'
        if summary:
            data += f'test_summary = "{summary}"\n'
        data += '[coverage]\ndocumentation = ["*.md"]\n'
        (self.root / 'tools/harness').mkdir(parents=True, exist_ok=True)
        (self.root / 'tools/harness/harness.toml').write_text(data)

    def probe(self, code="print('ok')"):
        (self.root / "probe.py").write_text(code)


class VerificationTests(Workspace):
    def test_unittest_failure_with_exit_zero_cannot_be_reported_as_passed(self):
        samples = ["Ran 1 test in 0.001s\nFAILED (failures=1)\n",
                   "Ran 1 test in 0.001s\nFAILED (errors=1)\n",
                   "Ran 1 test in 0.001s\nFAILED (unexpected successes=1)\n",
                   "Ran 1 test in 0.001s\nOK (failures=1)\n",
                   "FAIL: test_owner\nRan 1 test in 0.001s\nOK\n",
                   "Ran 1 test in 0.001s\nFAILED (failures=1)\nRan 1 test in 0.001s\nOK\n"]
        self.config(summary="unittest")
        for output in samples:
            with self.subTest(output=output):
                self.probe("print(" + repr(output) + ")")
                result = checks.run(self.root, ["probe.py"])
                self.assertEqual(result["status"], "failed")
                self.assertGreater(result["results"][0]["failed_count"], 0)

    def test_unittest_missing_contradictory_and_impossible_reports_are_not_passes(self):
        self.config(summary="unittest")
        for output in ["Ran 1 test in 0.001s", "OK", "Ran 1 test in 0.001s\nOK\nFAILED (failures=1)",
                       "Ran 1 test in 0.001s\nOK (skipped=2)", "Ran 1 test in 0.001s\nOK (skipped=-1)",
                       "Ran 1 test in 0.001s\nOK (skipped=0, skipped=0)"]:
            with self.subTest(output=output):
                self.probe("print(" + repr(output) + ")")
                result = checks.run(self.root, ["probe.py"])
                self.assertEqual(result["results"][0]["status"], "invalid_test_report")

    def test_all_expected_failures_do_not_prove_passing_behavior(self):
        self.config(summary="unittest")
        self.probe("print('Ran 1 test in 0.001s'); print('OK (expected failures=1)')")
        result = checks.run(self.root, ["probe.py"])
        self.assertEqual(result["results"][0]["status"], "no_tests_executed")
        self.assertEqual(result["results"][0]["expected_failure_count"], 1)

    def test_multiple_valid_unittest_runs_preserve_all_execution_and_skip_counts(self):
        self.config(summary="unittest")
        self.probe("print('Ran 2 tests in 0.001s\\nOK (skipped=1)\\nRan 3 tests in 0.001s\\nOK (expected failures=1)')")
        result = checks.run(self.root, ["probe.py"])
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["results"][0]["test_count"], 5)
        self.assertEqual(result["results"][0]["skipped_count"], 1)

    def test_real_policy_does_not_misclassify_embedded_project_code_as_docs(self):
        result = checks.plan(SOURCE, ["docs/projects/demo/backend/main.py", "docs/tasks/demo/helper.py"])
        self.assertEqual(len(result["uncovered_paths"]), 2)

    def test_unknown_new_app_is_not_covered_by_harness_tests(self):
        self.probe()
        result = checks.run(self.root, ["frontend/src/New.svelte"])
        self.assertEqual(result["status"], "needs_configuration")
        self.assertFalse(result["results"])

    def test_docs_change_does_not_run_unrelated_behavior_tests(self):
        self.probe("raise RuntimeError('must not execute')")
        result = checks.plan(self.root, ["README.md"])
        self.assertEqual(result["checks"], [])
        self.assertEqual(result["uncovered_paths"], [])

    def test_failure_exit_and_raw_log_survive(self):
        self.probe("print('specific regression'); raise SystemExit(7)")
        result = checks.run(self.root, ["probe.py"])
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["results"][0]["exit_code"], 7)
        self.assertIn("specific regression", Path(result["results"][0]["log"]).read_text())
        self.assertFalse(result["product_accepted"])

    def test_unchanged_result_reused_but_source_change_invalidates_it(self):
        self.probe()
        first = checks.run(self.root, ["probe.py"])
        self.assertEqual(first["status"], "passed")
        second = checks.run(self.root, ["probe.py"], reuse=True)
        self.assertTrue(second["results"][0]["reused"])
        self.probe("raise SystemExit(2)")
        third = checks.run(self.root, ["probe.py"], reuse=True)
        self.assertFalse(third["results"][0]["reused"])
        self.assertEqual(third["status"], "failed")

    def test_environment_change_invalidates_fingerprint(self):
        before = fingerprint(self.root)
        with patch.dict(os.environ, {"HARNESS_EXPERIMENT_CONDITION": "changed"}):
            self.assertNotEqual(before, fingerprint(self.root))

    def test_transport_trace_id_does_not_invalidate_identical_execution(self):
        with patch.dict(os.environ, {"CODEX_TOOL_CALL_ID": "first"}):
            before = fingerprint(self.root)
        with patch.dict(os.environ, {"CODEX_TOOL_CALL_ID": "second"}):
            self.assertEqual(before, fingerprint(self.root))

    def test_local_environment_affects_reuse_but_is_not_selected_as_app_source(self):
        self.probe()
        before = fingerprint(self.root)
        (self.root / ".env").write_text("LOCAL_CONDITION=changed\n")
        self.assertNotEqual(before, fingerprint(self.root))
        self.assertNotIn(".env", source_paths(self.root))

    def test_changes_after_success_make_evidence_stale(self):
        self.probe("from pathlib import Path; Path('new-source.py').write_text('changed')")
        result = checks.run(self.root, ["probe.py"])
        self.assertEqual(result["results"][0]["status"], "passed")
        self.assertEqual(result["status"], "stale")

    def test_zero_discovered_tests_are_not_a_pass(self):
        (self.root / "tests").mkdir()
        self.config(["{python}", "-m", "unittest", "discover", "-s", "tests"], "unittest")
        result = checks.run(self.root, ["probe.py"])
        self.assertEqual(result["results"][0]["test_count"], 0)
        self.assertEqual(result["status"], "failed")

    def test_all_skipped_tests_are_not_a_pass(self):
        testdir = self.root / "tests"
        testdir.mkdir()
        (testdir / "test_skip.py").write_text("import unittest\nclass T(unittest.TestCase):\n @unittest.skip('not available')\n def test_x(self): pass\n")
        self.config(["{python}", "-m", "unittest", "discover", "-s", "tests"], "unittest")
        result = checks.run(self.root, ["probe.py"])
        self.assertEqual(result["results"][0]["status"], "no_tests_executed")

    def test_path_escape_is_rejected(self):
        with self.assertRaises(ValueError):
            checks.plan(self.root, ["../outside.py"])

    def test_arguments_are_not_shell_commands(self):
        self.config(["{python}", "-c", "import sys; print(sys.argv[1])", "; touch injected"], patterns=["**"])
        result = checks.run(self.root, ["probe.py"])
        self.assertEqual(result["status"], "passed")
        self.assertFalse((self.root / "injected").exists())


class SetupAndTaskTests(Workspace):
    def canonical(self, content):
        source = self.root / ".agents/skills/example/SKILL.md"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(content)
        return source

    def configure_codex(self):
        self.canonical("---\nname: example\ndescription: Example task guidance.\n---\nProject instructions.\n")
        (self.root / "AGENTS.md").write_text("# Project instructions\n")
        for name in [".codex/config.toml", ".codex/hooks.json", "tools/harness/run.py", "tools/harness/route_prompt.py", "tools/harness/browser/package.json", "tools/harness/browser/package-lock.json"]:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(SOURCE / name, target)

    def test_native_skill_setup_is_idempotent_and_preserves_all_sources(self):
        self.configure_codex()
        def snapshot():
            return {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        before = snapshot()
        self.assertEqual(setup(self.root)["status"], "passed")
        self.assertEqual(setup(self.root)["status"], "passed")
        self.assertEqual(snapshot(), before)

    def test_doctor_accepts_agreed_postgres_and_legacy_stack_but_rejects_drift(self):
        self.configure_codex()
        path = self.root / "tools/harness/harness.toml"
        original = path.read_text()
        for database, accepted in [(None, True), ("postgresql", True), ("mysql", False)]:
            with self.subTest(database=database):
                value = original if database is None else original.replace(
                    'backend = "python"\n', f'backend = "python"\ndatabase = "{database}"\n')
                path.write_text(value)
                result = doctor.inspect(self.root)
                self.assertEqual(result["status"], "passed" if accepted else "failed")
                if not accepted:
                    self.assertTrue(any("base stack" in error for error in result["errors"]))

    def test_setup_reports_missing_project_config_without_creating_it(self):
        result = setup(self.root)
        self.assertEqual(result["status"], "failed")
        self.assertFalse((self.root / ".codex/config.toml").exists())

    def test_mcp_check_reads_codex_config(self):
        self.configure_codex()
        output = io.StringIO()
        with patch("harness.cli.mcp.probe", return_value={"status": "passed", "tool_count": 1}) as probe_mock:
            with redirect_stdout(output):
                code = main(["mcp-check"], root=self.root)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())["status"], "passed")
        self.assertEqual({c.args[0] for c in probe_mock.call_args_list},
                         {"https://developers.openai.com/mcp", "https://mcp.svelte.dev/mcp"})

    def test_task_records_require_criteria_and_do_not_claim_completion(self):
        path = tasks.create(self.root, "compare-api-clients", "research", "Compare options", ["Cite primary evidence"])
        data = json.loads(path.read_text())
        self.assertEqual(data["status"], "planned")
        self.assertEqual(data["acceptance"][0]["status"], "pending")
        with self.assertRaises(FileExistsError):
            tasks.create(self.root, "compare-api-clients", "research", "Overwrite", ["x"])
        with self.assertRaises(ValueError):
            tasks.create(self.root, "../escape", "research", "x", ["x"])

    def test_completed_task_with_pending_or_missing_evidence_is_invalid(self):
        path = tasks.create(self.root, "example", "implement", "Save data", ["Data persists"])
        data = json.loads(path.read_text())
        self.assertEqual(tasks.validate(data), [])
        data["status"] = "complete"
        self.assertTrue(tasks.validate(data))
        data["acceptance"][0].update(status="passed", method="API integration test", evidence=["results/report.json"])
        self.assertTrue(tasks.validate(data))

    def test_protocol_probe_does_not_wait_for_sse_connection_close(self):
        class Response(io.BytesIO):
            def __init__(self, value, sse=False):
                encoded = json.dumps(value) if value else ""
                super().__init__((f"data: {encoded}\n\n" if sse else encoded).encode())
                self.headers = {"Content-Type": "text/event-stream" if sse else "application/json"}
                self.status = 200 if value else 202
            def read(self, *args):
                if self.headers["Content-Type"] == "text/event-stream":
                    raise AssertionError("must read an event, not wait for the entire persistent stream")
                return super().read(*args)
        replies = [Response({"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2025-03-26"}}, True), Response(None),
                   Response({"jsonrpc": "2.0", "id": 2, "result": {"tools": [{"name": "search_docs"}]}}, True)]
        with patch("harness.mcp.urlopen", side_effect=replies) as request:
            result = probe("https://example.test/mcp")
        self.assertEqual(result["status"], "passed")
        methods = [json.loads(call.args[0].data)["method"] for call in request.call_args_list]
        self.assertEqual(methods, ["initialize", "notifications/initialized", "tools/list"])

    def test_mcp_accepts_json_and_sse_results_not_html(self):
        value = {"jsonrpc": "2.0", "id": 1, "result": {"tools": []}}
        self.assertEqual(decode(json.dumps(value)), value)
        self.assertEqual(decode("event: message\ndata: " + json.dumps(value) + "\n"), value)
        with self.assertRaises(ValueError):
            decode("<html>not MCP</html>")


@unittest.skipUnless(shutil.which("git"), "Git required for exact-index test")
class SnapshotTests(Workspace):
    def test_unstaged_helper_cannot_make_incomplete_index_pass(self):
        def git(*args):
            subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True)
        git("init", "-q")
        shutil.copytree(SOURCE / "tools/harness/harness", self.root / "tools/harness/harness", ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copy2(SOURCE / "tools/harness/run.py", self.root / "tools/harness/run.py")
        self.config(patterns=["**"])
        self.probe("import unstaged_helper; print('ok')")
        git("add", "tools/harness/harness.toml", "probe.py", "tools/harness")
        (self.root / "unstaged_helper.py").write_text("value = 1\n")
        working = checks.run(self.root, ["probe.py"])
        self.assertEqual(working["status"], "passed")
        staged = checks.staged(self.root)
        self.assertEqual(staged["status"], "failed")
        self.assertEqual(staged["snapshot"], "git_index")
        self.assertIn("unstaged_helper", Path(staged["results"][0]["log"]).read_text())
        self.assertEqual((self.root / "unstaged_helper.py").read_text(), "value = 1\n")
        git("add", "unstaged_helper.py")
        complete = checks.staged(self.root)
        self.assertEqual(complete["status"], "passed")
        self.assertEqual(complete["snapshot"], "git_index")
