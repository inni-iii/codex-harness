"""Adversarial local fixtures for provenance, files and parser budgets."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from _support import SOURCE
from harness import checks, core, provenance, security


class FinalBoundaryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='harness-final-security-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        config = self.root / 'tools/harness/harness.toml'
        config.parent.mkdir(parents=True)
        config.write_text('version=1\n[[checks]]\nid="policy"\ncommand=["{python}","probe.py"]\npaths=["**"]\ncacheable=true\n')
        (self.root / 'probe.py').write_text("from pathlib import Path\nassert Path('backend/build/policy.txt').read_text() == 'allowed'\n")
        policy = self.root / 'backend/build/policy.txt'
        policy.parent.mkdir(parents=True)
        policy.write_text('allowed')

    def test_tracked_source_under_artifact_directory_participates_in_cache_and_evidence(self):
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True, capture_output=True)
        subprocess.run(['git', 'add', '-f', 'backend/build/policy.txt'], cwd=self.root, check=True, capture_output=True)
        first = checks.run(self.root, ['probe.py'])
        self.assertEqual(first['status'], 'passed')
        self.assertIn('backend/build/policy.txt', first['source_snapshot'])
        (self.root / 'backend/build/policy.txt').write_text('denied')
        result = checks.run(self.root, ['probe.py'], reuse=True)
        self.assertEqual(result['status'], 'failed')
        self.assertFalse(result['results'][0]['reused'])

    def test_project_named_build_is_included_in_source_archives(self):
        path = self.root / 'docs/projects/build/security.md'
        path.parent.mkdir(parents=True)
        path.write_text('Protect a synthetic resource')
        self.assertIn('docs/projects/build/security.md', provenance.snapshot(self.root))

    def test_environment_template_is_scanned_in_source_archives_without_echoing_secret(self):
        value = 'SYNTHETIC_INVALID_' + 'Q' * 20
        (self.root / '.env.example').write_text('TOKEN=' + value)
        result = security.secrets(self.root)
        self.assertEqual(result['status'], 'findings')
        self.assertIn('.env.example', {f['path'] for f in result['findings']})
        self.assertNotIn(value, json.dumps(result))

    def test_default_runtime_symlink_is_rejected_before_execution(self):
        with tempfile.TemporaryDirectory(prefix='harness-outside-results-') as outside:
            (self.root / '.runtime').symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                checks.run(self.root, ['probe.py'])
            self.assertEqual(list(Path(outside).iterdir()), [])

    def test_malformed_cache_is_a_miss_and_never_a_pass(self):
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True, capture_output=True)
        subprocess.run(['git', 'add', '-f', 'backend/build/policy.txt'], cwd=self.root, check=True, capture_output=True)
        cache = self.root / '.runtime/check-cache.json'
        cache.parent.mkdir()
        cache.write_text('[]')
        result = checks.run(self.root, ['probe.py'], reuse=True)
        self.assertEqual(result['status'], 'passed')
        self.assertFalse(result['results'][0]['reused'])

    def test_junit_node_limit_accepts_boundary_and_rejects_next_node(self):
        report = self.root / 'report.xml'
        report.write_text('<testsuite><testcase/><testcase/></testsuite>')
        with patch('harness.checks.MAX_JUNIT_NODES', 3):
            self.assertEqual(checks.junit_counts(report)['test_count'], 2)
            report.write_text('<testsuite><testcase/><testcase/><testcase/></testsuite>')
            with self.assertRaises(ValueError):
                checks.junit_counts(report)

    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'FIFO support')
    def test_nonregular_inputs_are_rejected_without_waiting_for_a_writer(self):
        pipe = self.root / 'pipe'
        os.mkfifo(pipe)
        code = f'''import sys
from pathlib import Path
sys.path.insert(0,{str(SOURCE / 'tools/harness')!r})
from harness import core,checks,provenance as p
root=Path({str(self.root)!r});pipe=root/'pipe'
for call in (lambda:core.fingerprint(root),lambda:checks.junit_counts(pipe),lambda:p.load(pipe),lambda:p.sha(pipe)):
 try:call()
 except ValueError:pass
 else:raise AssertionError('nonregular input was accepted')
assert not checks.intact({{'log':str(pipe),'log_sha256':'0'*64}})
'''
        try:
            result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, timeout=2)
        except subprocess.TimeoutExpired:
            self.fail('Nonregular input blocked waiting for a writer')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_json_read_is_bounded_even_if_stat_report_would_be_small(self):
        report = self.root / 'report.json'
        report.write_text(json.dumps({'value': 'x' * 100}))
        with self.assertRaisesRegex(ValueError, 'size limit'):
            provenance.load(report, limit=10)

    def test_excluded_existing_sources_are_not_silently_covered_by_a_broad_check(self):
        result = checks.run(self.root, ['backend/build/policy.txt'])
        self.assertEqual(result['status'], 'needs_configuration')
        self.assertEqual(result['results'], [])

    def test_execution_and_knowledge_configuration_select_behavioral_regressions(self):
        for path in ('.codex/hooks.json', 'tools/harness/security/package.json', 'docs/knowledge/catalog.json', 'tools/harness/route_prompt.py'):
            selected = checks.plan(SOURCE, [path])
            self.assertEqual(selected['uncovered_paths'], [])
            self.assertIn('python', [c['id'] for c in selected['checks']])

    def test_metadata_hook_rejects_payloads_hidden_inside_status(self):
        from harness import knowledge_hooks
        path = self.root / 'docs/tasks/demo/task.json'
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({'status': {'payload': 'synthetic private task content'}}))
        with self.assertRaisesRegex(ValueError, 'state'):
            knowledge_hooks.handle(self.root, {'hook_event_name': 'Stop', 'session_id': 'synthetic-session'})
        self.assertFalse((self.root / '.runtime/knowledge-events').exists())

    def test_failed_subtests_are_real_failures_not_invalid_runner_reports(self):
        command = ['{python}', '-c', 'import unittest\nclass Matrix(unittest.TestCase):\n def test_boundary(self):\n  for value in range(3):\n   with self.subTest(value=value): self.assertEqual(value,-1)\nunittest.main()']
        config = self.root / 'tools/harness/harness.toml'
        config.write_text('version=1\n[[checks]]\nid="matrix"\ncommand=' + json.dumps(command) + '\npaths=["**"]\ntest_summary="unittest"\n')
        result = checks.run(self.root, ['probe.py'])
        self.assertEqual(result['status'], 'failed')
        record = result['results'][0]
        self.assertIsNone(record['summary_error'])
        self.assertEqual(record['test_count'], 1)
        self.assertEqual(record['failed_count'], 3)

    def test_captured_runner_rejects_outside_paths_and_malformed_success(self):
        base = self.root / '.runtime/private-reports'
        outside = self.root / 'outside.json'
        outside.write_text(json.dumps({'status': 'passed', 'results': []}))
        for value in ({'report': str(outside)}, {'status': 'passed', 'results': []}, [],
                      {'status': 'passed', 'results': None}):
            code = 'print(' + repr(json.dumps(value)) + ')'
            result = checks.captured_run([sys.executable, '-c', code], self.root, base)
            self.assertEqual(result['status'], 'invalid_snapshot_result')
            self.assertFalse(result['completion_ready'])
        self.assertEqual(json.loads(outside.read_text()), {'status': 'passed', 'results': []})

    def test_captured_runner_output_and_time_are_bounded(self):
        base = self.root / '.runtime/private-reports'
        for code, timeout in [("print('x' * (5 * 1024 * 1024))", 3), ('import time; time.sleep(5)', .05)]:
            result = checks.captured_run([sys.executable, '-c', code], self.root, base, timeout=timeout)
            self.assertEqual(result['status'], 'invalid_snapshot_result')
            self.assertTrue(result.get('execution_error'))
        self.assertTrue(all(p.stat().st_size < 4 * 1024 * 1024 + 256 for p in base.glob('*/runner.log')))

    def test_nonzero_captured_runner_cannot_override_exit_with_a_valid_green_report(self):
        base = self.root / '.runtime/private-reports'
        code = f'''import sys,json
from pathlib import Path
sys.path.insert(0,{str(SOURCE / 'tools/harness')!r})
from harness import provenance as p
root=Path.cwd()
folder=Path({str(base)!r})/'fixture'
folder.mkdir(parents=True,exist_ok=True)
log=folder/'check.log'
log.write_text('synthetic runner contract fixture')
report={{'status':'passed','workspace':str(root),'source_snapshot':p.snapshot(root),
 'source_executable':p.executable_snapshot(root),'environment':p.environment(),
 'results':[{{'check':'synthetic','status':'passed','exit_code':0,'covers_behavior':True,
 'log':str(log),'log_sha256':p.sha(log)}}]}}
path=folder/'report.json'
p.atomic(path,report)
print(json.dumps({{'report':str(path)}}))
raise SystemExit(int(sys.argv[1]))
'''
        accepted = checks.captured_run([sys.executable, '-c', code, '0'], self.root, base)
        self.assertEqual(accepted['status'], 'passed', accepted)
        rejected = checks.captured_run([sys.executable, '-c', code, '1'], self.root, base)
        self.assertEqual(rejected['status'], 'invalid_snapshot_result')
        self.assertFalse(rejected['completion_ready'])
