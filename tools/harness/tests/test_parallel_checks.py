"""Real concurrent edits cannot change a captured check or become current proof."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from _support import SOURCE
from harness import check_snapshots, evidence, provenance, security


class SnapshotChecksTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="parallel-checks-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        # Match real artifact exclusions when a scenario initializes Git.
        shutil.copy2(SOURCE / '.gitignore', self.root / '.gitignore')
        shutil.copytree(SOURCE / "tools/harness/harness", self.root / "tools/harness/harness",
                        ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copy2(SOURCE / "tools/harness/run.py", self.root / "tools/harness/run.py")
        (self.root / "tools/harness/harness.toml").write_text('''version=1
[[checks]]
id="unit"
command=["{python}","probe.py"]
paths=["**"]
test_summary="unittest"
''')
        (self.root / "input.txt").write_text("original")
        self.probe()

    def probe(self, signal=False):
        code = "from pathlib import Path\nimport time\n"
        if signal:
            marker = self.root / ".runtime/started"
            marker.parent.mkdir(exist_ok=True)
            code += f"Path({str(marker)!r}).touch()\ntime.sleep(0.25)\n"
        code += "assert Path('input.txt').read_text() == 'original'\nprint('Ran 1 test in 0.001s')\nprint('OK')\n"
        (self.root / "probe.py").write_text(code)

    def entry(self, result):
        path = Path(result["report"])
        return {"type": "check", "path": path.relative_to(self.root).as_posix(),
                "sha256": provenance.sha(path), "description": "Read captured input", "check": "unit"}

    def test_check_remains_valid_for_snapshot_when_another_session_changes_live_source(self):
        self.probe(signal=True)
        errors = []
        def edit():
            deadline = time.monotonic() + 10
            while not (self.root / ".runtime/started").exists():
                if time.monotonic() > deadline:
                    errors.append("captured command never started")
                    return
                time.sleep(0.005)
            (self.root / "input.txt").write_text("changed by another session")
        writer = threading.Thread(target=edit)
        writer.start()
        try:
            result = check_snapshots.run(self.root, ["input.txt"])
        finally:
            writer.join(timeout=11)
        self.assertEqual(errors, [])
        self.assertEqual(result["status"], "passed", result)
        self.assertTrue(result["live_source_changed"])
        self.assertEqual((self.root / "input.txt").read_text(), "changed by another session")
        self.assertEqual((Path(result["snapshot_directory"]) / "input.txt").read_text(), "original")
        with self.assertRaisesRegex(ValueError, "stale"):
            evidence.verify_entry(self.root, self.entry(result), self.root / "docs/tasks/demo/task.json")

    def test_unchanged_snapshot_is_reusable_as_current_evidence_but_not_in_another_workspace(self):
        result = check_snapshots.run(self.root, ["input.txt"])
        self.assertEqual(result["status"], "passed", result)
        self.assertFalse(result["live_source_changed"])
        evidence.verify_entry(self.root, self.entry(result), self.root / "docs/tasks/demo/task.json")
        report = json.loads(Path(result["report"]).read_text())
        report["snapshot_origin"] = str(self.root.parent / "another-workspace")
        with self.assertRaisesRegex(ValueError, "different workspace"):
            evidence.current_sources(self.root, report, self.root / "docs/tasks/demo/task.json")

    def test_source_change_during_capture_runs_no_commands(self):
        with patch("harness.check_snapshots.fingerprint", side_effect=["before", "after"]):
            result = check_snapshots.run(self.root, ["input.txt"])
        self.assertEqual(result["status"], "capture_changed")
        self.assertFalse(any((self.root / ".runtime/check-snapshots").glob("*/checks/*/report.json")))

    def test_transient_capture_content_cannot_pass_just_because_source_fingerprint_returned(self):
        original_read = Path.read_bytes
        def transient_read(path):
            return b"intermediate edit" if path == self.root / "input.txt" else original_read(path)
        with patch("harness.check_snapshots.fingerprint", return_value="unchanged"), patch.object(Path, "read_bytes", transient_read):
            result = check_snapshots.run(self.root, ["input.txt"])
        self.assertEqual(result["status"], "capture_changed")
        self.assertFalse(any((self.root / ".runtime/check-snapshots").glob("*/checks/*/report.json")))

    def test_private_ignored_environment_is_not_copied_and_does_not_borrow_current_evidence(self):
        (self.root / ".env").write_text("LOCAL_SETTING=private\n")
        result = check_snapshots.run(self.root, ["input.txt"])
        self.assertEqual(result["status"], "passed", result)
        self.assertFalse((Path(result["snapshot_directory"]) / ".env").exists())
        with self.assertRaisesRegex(ValueError, "stale"):
            evidence.verify_entry(self.root, self.entry(result), self.root / "docs/tasks/demo/task.json")

    def test_empty_scope_is_not_a_pass(self):
        result = check_snapshots.run(self.root, [])
        self.assertEqual(result["status"], "no_checks")

    def test_snapshot_preserves_explicit_tracked_inputs_under_ignored_directories(self):
        path = self.root / 'backend/build/policy.py'
        path.parent.mkdir(parents=True)
        path.write_text('policy = "synthetic"\n')
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True, capture_output=True)
        subprocess.run(['git', 'add', '-f', 'backend/build/policy.py'], cwd=self.root, check=True, capture_output=True)
        result = check_snapshots.run(self.root, ['input.txt'])
        self.assertEqual(result['status'], 'passed', result)
        self.assertIn('backend/build/policy.py', result['source_snapshot'])
        evidence.verify_entry(self.root, self.entry(result), self.root / 'docs/tasks/demo/task.json')

    def test_explicitly_tracked_environment_is_not_silently_omitted_by_snapshot_scanner(self):
        (self.root / '.env').write_text('TOKEN=' + 'SYNTHETIC_INVALID_' + 'Q' * 20)
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True, capture_output=True)
        subprocess.run(['git', 'add', '-f', '.env'], cwd=self.root, check=True, capture_output=True)
        result = check_snapshots.run(self.root, ['input.txt'])
        self.assertEqual(result['status'], 'passed', result)
        scanned = security.secrets(Path(result['snapshot_directory']))
        self.assertEqual(scanned['status'], 'findings')
        self.assertIn('.env', {f['path'] for f in scanned['findings']})
