"""Execute real local children, runner reports and Make recipes in isolation."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from _support import SOURCE
from harness import checks
from harness.processes import execute


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='harness-execution-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def run_command(self, code, **options):
        return execute([sys.executable, '-c', code], cwd=self.root,
                       log=self.root / '.runtime/output.log', **options)

    def test_output_limit_stops_flood_and_bounds_log(self):
        result = self.run_command("import os\nwhile True: os.write(1, b'x'*65536)", timeout=3, max_output_bytes=1024)
        self.assertIn(result['error'], ('output_limit', 'process_group_cleanup_denied'))
        self.assertLess((self.root / '.runtime/output.log').stat().st_size, 1200)

    def test_exit_code_and_execution_error_are_preserved(self):
        self.assertEqual(self.run_command('raise SystemExit(7)', timeout=2)['exit_code'], 7)
        result = execute(['/nonexistent/harness-command'], cwd=self.root,
                         log=self.root / '.runtime/missing.log', timeout=1)
        self.assertEqual(result['error'], 'cannot_execute')

    @unittest.skipUnless(os.name == 'posix', 'POSIX process-group contract')
    def test_timeout_cleans_descendants_even_when_parent_exits_first(self):
        for parent_exit in (False, True):
            with self.subTest(parent_exit=parent_exit):
                child = "import time; from pathlib import Path; time.sleep(0.6); Path('.runtime/leaked').touch()"
                code = 'import subprocess,sys,time; subprocess.Popen([sys.executable,"-c",' + repr(child) + ']); '
                code += 'sys.exit(0)' if parent_exit else 'time.sleep(5)'
                result = self.run_command(code, timeout=0.15)
                time.sleep(0.65)
                if result['error'] == 'process_group_cleanup_denied':
                    self.skipTest('Execution sandbox denies group signals; fallback fails closed and kills root only')
                self.assertEqual(result['error'], 'timeout')
                self.assertFalse((self.root / '.runtime/leaked').exists())

    def configure(self, xml):
        folder = self.root / 'tools/harness'
        folder.mkdir(parents=True, exist_ok=True)
        cmd = ['{python}', '-c', 'from pathlib import Path; import sys; Path(sys.argv[1]).write_text(' + repr(xml) + ')', '{report}']
        (folder / 'harness.toml').write_text('version=1\n[[checks]]\nid="fixture"\npaths=["**"]\ncacheable=true\ntest_summary="junit"\ncommand=' + json.dumps(cmd))

    def test_retry_success_is_explicitly_flaky_and_not_a_default_pass(self):
        self.configure('<testsuite><testcase><flakyFailure>first attempt failed</flakyFailure></testcase></testsuite>')
        result = checks.run(self.root, ['example.py'])
        self.assertEqual(result['results'][0]['status'], 'flaky')
        self.assertEqual(result['results'][0]['flaky_count'], 1)
        config = self.root / 'tools/harness/harness.toml'
        config.write_text(config.read_text() + '\nallow_flaky=true\n')
        accepted = checks.run(self.root, ['example.py'])
        self.assertEqual(accepted['status'], 'passed')
        self.assertEqual(accepted['results'][0]['flaky_count'], 1)

    @unittest.skipUnless(os.name == 'posix', 'POSIX signal-denied fallback')
    def test_group_permission_failure_is_reported_without_a_false_pass(self):
        with patch('harness.processes.os.killpg', side_effect=PermissionError('denied')):
            result = self.run_command('import time; time.sleep(5)', timeout=0.05)
        self.assertEqual(result['error'], 'process_group_cleanup_denied')
        self.assertNotEqual(result['exit_code'], 0)

    def test_tampered_cached_report_and_log_force_a_new_execution(self):
        self.configure('<testsuite><testcase name="valid"/></testsuite>')
        for field in ('log', 'test_report'):
            first = checks.run(self.root, ['example.py'])
            Path(first['results'][0][field]).write_text('tampered')
            second = checks.run(self.root, ['example.py'], reuse=True)
            self.assertFalse(second['results'][0]['reused'])
            self.assertEqual(second['status'], 'passed')

    @unittest.skipUnless(os.name == 'posix', 'POSIX execute permissions')
    def test_removed_execute_permission_cannot_reuse_a_pass(self):
        script = self.root / 'probe'
        script.write_text('#!' + sys.executable + '\nprint("fixture passed")\n')
        script.chmod(0o700)
        config = self.root / 'tools/harness/harness.toml'
        config.parent.mkdir(parents=True)
        config.write_text('version=1\n[[checks]]\nid="script"\ncommand=["./probe"]\npaths=["**"]\ncacheable=true\n')
        self.assertEqual(checks.run(self.root, ['probe'])['status'], 'passed')
        script.chmod(0o600)
        result = checks.run(self.root, ['probe'], reuse=True)
        self.assertEqual(result['status'], 'failed')
        self.assertFalse(result['results'][0]['reused'])

    def test_makefile_has_behavior_coverage(self):
        result = checks.plan(SOURCE, ['Makefile'])
        self.assertIn('python', [c['id'] for c in result['checks']])
        self.assertEqual(result['uncovered_paths'], [])

    @unittest.skipUnless(shutil.which('make'), 'make unavailable')
    def test_actual_make_recipes_forward_checkpoints_and_propagate_failure(self):
        shutil.copytree(SOURCE / 'tools/harness/harness', self.root / 'tools/harness/harness', ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copy(SOURCE / 'tools/harness/run.py', self.root / 'tools/harness/run.py')
        shutil.copy(SOURCE / 'Makefile', self.root / 'Makefile')
        shutil.copy(SOURCE / '.gitignore', self.root / '.gitignore')
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True, capture_output=True)
        self.configure('<testsuite><testcase name="valid"/></testsuite>')
        for target, checkpoint in [('check-quick', 'edit'), ('check-feature', 'feature'), ('check-full', 'feature')]:
            proc = subprocess.run(['make', target, 'PYTHON=' + sys.executable], cwd=self.root, capture_output=True, text=True, timeout=10)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn('"checkpoint": "' + checkpoint + '"', proc.stdout)
        self.configure('<testsuite><testcase><failure/></testcase></testsuite>')
        proc = subprocess.run(['make', 'check-feature', 'PYTHON=' + sys.executable], cwd=self.root, capture_output=True, text=True, timeout=10)
        self.assertNotEqual(proc.returncode, 0)
