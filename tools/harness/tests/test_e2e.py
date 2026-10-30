"""Exercise E2E routing and runner/report integration, without pretending to test a product."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from _support import SOURCE

from harness import checks, context

ASSETS = SOURCE / '.agents/skills/e2e-testing/assets'
NODE = shutil.which('node')


class E2EContextTests(unittest.TestCase):
    def selected(self, kind, paths, topics):
        return {d['path']: d.get('content', '') for d in
                context.select(SOURCE, kind, paths, topics, read=True)['documents']}

    def test_interactive_svelte_change_reads_e2e_procedure_and_scenarios(self):
        docs = self.selected('implement', ['frontend/src/ItemForm.svelte'], [])
        self.assertIn('.agents/skills/e2e-testing/SKILL.md', docs)
        self.assertIn('.agents/skills/e2e-testing/references/scenarios.md', docs)
        self.assertNotIn('.agents/skills/e2e-testing/references/failures.md', docs)

    def test_playwright_setup_and_debug_select_relevant_references(self):
        setup = self.selected('plan', [], ['playwright'])
        self.assertIn('.agents/skills/e2e-testing/references/setup.md', setup)
        debug = self.selected('debug', [], ['e2e'])
        self.assertIn('.agents/skills/e2e-testing/references/failures.md', debug)

    def test_pure_backend_work_does_not_load_browser_manuals(self):
        docs = self.selected('implement', ['backend/calculation.py'], ['python'])
        self.assertFalse(any('/e2e-testing/' in p for p in docs))
        debug = self.selected('debug', ['backend/calculation.py'], [])
        self.assertFalse(any('/e2e-testing/' in p for p in debug))


@unittest.skipUnless(NODE, 'Node is required to exercise the optional Playwright bridge')
class PlaywrightBridgeTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='harness-e2e-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.app = self.root / 'app with spaces $(literal)'
        self.app.mkdir()
        self.report = self.root / '.runtime/run.xml'
        self.script = self.root / 'tools/harness/scripts/run-playwright.mjs'
        self.script.parent.mkdir(parents=True)
        shutil.copyfile(SOURCE / 'tools/harness/scripts/run-playwright.mjs', self.script)
        (self.app / 'playwright.config.cjs').write_text('// fixture config\n')
        self.pkg = self.app / 'node_modules/@playwright/test'

    def runner(self, xml='<testsuite><testcase name="flow"/></testsuite>', exit_code=0):
        self.pkg.mkdir(parents=True, exist_ok=True)
        (self.pkg / 'package.json').write_text('{"name":"@playwright/test","version":"0.0.0-fixture"}')
        (self.pkg / 'cli.js').write_text('''const fs = require('node:fs');
fs.mkdirSync('.runtime', {recursive: true});
fs.writeFileSync('.runtime/observed.json', JSON.stringify({argv: process.argv.slice(2),
  cwd: process.cwd(), report: process.env.HARNESS_JUNIT_REPORT,
  artifacts: process.env.HARNESS_E2E_ARTIFACTS}));
''' + (f'fs.writeFileSync(process.env.HARNESS_JUNIT_REPORT, {json.dumps(xml)});\n' if xml is not None else '')
            + f'process.exitCode = {exit_code};\n')

    def run_bridge(self, *extra):
        return subprocess.run([NODE, str(self.script), '--project-dir', self.app.name,
                               '--report', str(self.report), *extra], cwd=self.root,
                              capture_output=True, text=True, timeout=15)

    def test_local_runner_gets_literal_filters_and_fresh_artifact_paths(self):
        self.runner()
        result = self.run_bridge('--', '--grep', '@smoke $(literal)')
        self.assertEqual(result.returncode, 0, result.stderr)
        seen = json.loads((self.app / '.runtime/observed.json').read_text())
        self.assertEqual(seen['argv'], ['test', '--grep', '@smoke $(literal)'])
        self.assertEqual(Path(seen['cwd']).resolve(), self.app.resolve())
        self.assertEqual(Path(seen['report']), self.report)
        self.assertEqual(Path(seen['artifacts']), self.root / '.runtime/run-artifacts')
        self.assertTrue(self.report.is_file())

    def test_missing_runner_fails_without_implicit_install(self):
        result = self.run_bridge()
        self.assertEqual(result.returncode, 2)
        self.assertIn('Project-local @playwright/test is missing', result.stderr)
        self.assertFalse(self.pkg.exists())

    def test_existing_report_and_reporter_override_are_rejected(self):
        self.runner()
        self.report.parent.mkdir()
        self.report.write_text('old evidence')
        result = self.run_bridge()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.report.read_text(), 'old evidence')
        self.report.unlink()
        for option in ['--reporter=line', '--reporter', '--output=elsewhere']:
            with self.subTest(option=option):
                result = self.run_bridge('--', option)
                self.assertEqual(result.returncode, 2)
                self.assertFalse((self.app / '.runtime/observed.json').exists())

    def test_nonzero_exit_and_missing_report_cannot_become_success(self):
        self.runner(exit_code=7)
        self.assertEqual(self.run_bridge().returncode, 7)
        self.report.unlink()
        self.runner(xml=None)
        result = self.run_bridge()
        self.assertEqual(result.returncode, 2)
        self.assertIn('no fresh JUnit report', result.stderr)

    def test_project_outside_repository_is_rejected(self):
        result = subprocess.run([NODE, str(self.script), '--project-dir', '..',
                                 '--report', str(self.report)], cwd=self.root,
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 2)
        self.assertIn('inside this repository', result.stderr)

    def test_harness_reads_actual_fresh_runner_report_and_rejects_empty_run(self):
        command = [NODE, 'tools/harness/scripts/run-playwright.mjs', '--project-dir', self.app.name,
                   '--report', '{report}']
        (self.root / 'tools/harness').mkdir(parents=True, exist_ok=True)
        (self.root / 'tools/harness/harness.toml').write_text('version = 1\n[[checks]]\nid = "ui-e2e"\n'
            + 'command = ' + json.dumps(command) + '\npaths = ["frontend/**"]\n'
            + 'test_summary = "junit"\ncacheable = false\ntimeout = 20\n')
        self.runner()
        result = checks.run(self.root, ['frontend/Form.svelte'])
        self.assertEqual(result['status'], 'passed', result)
        self.assertFalse(result['product_accepted'])
        self.runner(xml='<testsuite/>')
        result = checks.run(self.root, ['frontend/Form.svelte'])
        self.assertEqual(result['status'], 'failed', result)

    def config(self, **values):
        self.pkg.mkdir(parents=True, exist_ok=True)
        (self.pkg / 'index.js').write_text('exports.defineConfig = x => x; exports.devices = {"Desktop Chrome": {browserName:"chromium"}};')
        target = self.app / 'playwright.config.cjs'
        shutil.copyfile(ASSETS / 'playwright.config.cjs', target)
        env = {k: v for k, v in os.environ.items() if not k.startswith(('E2E_', 'HARNESS_'))}
        env.update(values)
        return subprocess.run([NODE, '-e', 'console.log(JSON.stringify(require(process.argv[1])))', str(target)],
                              cwd=self.app, env=env, capture_output=True, text=True, timeout=10)

    def test_config_manages_both_servers_and_preserves_junit_and_failure_evidence(self):
        result = self.config(E2E_BASE_URL='http://127.0.0.1:4173', E2E_START_COMMAND='npm run dev',
                             E2E_API_URL='http://localhost:8000/ready', E2E_API_START_COMMAND='python -m app',
                             HARNESS_JUNIT_REPORT=str(self.report), HARNESS_E2E_ARTIFACTS=str(self.root / 'artifacts'))
        self.assertEqual(result.returncode, 0, result.stderr)
        config = json.loads(result.stdout)
        self.assertEqual(len(config['webServer']), 2)
        self.assertTrue(all(not server['reuseExistingServer'] for server in config['webServer']))
        self.assertEqual(config['reporter'][1][1]['outputFile'], str(self.report))
        self.assertEqual(config['use']['trace'], 'retain-on-failure')
        self.assertEqual(config['retries'], 0)

    def test_config_requires_local_servers_and_explicit_existing_server_choice(self):
        for values in [{}, {'E2E_BASE_URL': 'https://example.com'},
                       {'E2E_BASE_URL': 'http://localhost:4173'},
                       {'E2E_BASE_URL': 'http://localhost:4173', 'E2E_START_COMMAND': 'npm run dev',
                        'E2E_API_URL': 'http://localhost:8000/ready'}]:
            with self.subTest(values=values):
                self.assertNotEqual(self.config(**values).returncode, 0)
        result = self.config(E2E_BASE_URL='http://localhost:4173', E2E_USE_EXISTING_SERVER='true')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['webServer'], [])


if __name__ == '__main__':
    unittest.main()
