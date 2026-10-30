"""Verification checkpoints defer expensive work explicitly, without a false pass."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from _support import SOURCE
from harness import checks


class CheckpointTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='harness-checkpoints-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        config = self.root / 'tools/harness/harness.toml'
        config.parent.mkdir(parents=True)
        # This tests runner selection/report plumbing, not a browser or product.
        xml = '<testsuite><testcase name="fixture"/></testsuite>'
        command = ['{python}', '-c', 'from pathlib import Path; Path(".runtime/e2e-ran").touch(); Path(__import__("sys").argv[1]).write_text(' + repr(xml) + ')', '{report}']
        config.write_text('''version = 1
[[checks]]
id = "fast"
command = ["{python}", "-c", "print('fast boundary check')"]
paths = ["frontend/**"]
[[checks]]
id = "e2e"
command = ''' + json.dumps(command) + '''
paths = ["frontend/**"]
run_at = ["feature", "integration", "final"]
test_summary = "junit"
cacheable = false
[coverage]
documentation = ["*.md"]
''')

    def test_edit_runs_fast_checks_and_reports_pending_e2e_then_feature_runs_it(self):
        result = checks.run(self.root, ['frontend/Form.svelte'], checkpoint='edit')
        self.assertEqual(result['status'], 'checkpoint_passed', result)
        self.assertEqual(result['deferred_checks'], ['e2e'])
        self.assertFalse((self.root / '.runtime/e2e-ran').exists())
        self.assertFalse(result['product_accepted'])
        result = checks.run(self.root, ['frontend/Form.svelte'], checkpoint='feature')
        self.assertEqual(result['status'], 'passed', result)
        self.assertEqual(result['deferred_checks'], [])
        self.assertTrue((self.root / '.runtime/e2e-ran').exists())
        self.assertEqual(result['results'][1]['test_count'], 1)

    def test_unknown_source_is_not_hidden_by_deferred_checks(self):
        result = checks.run(self.root, ['backend/new.py'], checkpoint='edit')
        self.assertEqual(result['status'], 'needs_configuration')
        self.assertEqual(result['uncovered_paths'], ['backend/new.py'])

    def test_no_selected_checks_is_deferred_instead_of_passed(self):
        config = self.root / 'tools/harness/harness.toml'
        config.write_text(config.read_text().replace('paths = ["frontend/**"]', 'paths = ["quick/**"]', 1))
        result = checks.run(self.root, ['frontend/Form.svelte'], checkpoint='edit')
        self.assertEqual(result['status'], 'deferred')
        self.assertEqual(result['deferred_checks'], ['e2e'])
        self.assertFalse(result['product_accepted'])

    def test_explicit_shared_impact_can_require_e2e_before_the_normal_checkpoint(self):
        config = self.root / 'tools/harness/harness.toml'
        config.write_text(config.read_text() + '\n[[impacts]]\npaths = ["frontend/auth/**"]\nchecks = ["e2e"]\nreason = "Shared auth requires immediate regression verification."\n')
        result = checks.plan(self.root, ['frontend/auth/session.ts'], checkpoint='edit')
        self.assertEqual({c['id'] for c in result['checks']}, {'fast', 'e2e'})
        self.assertEqual(result['deferred_checks'], [])
        self.assertIn('Shared auth', result['selection_reasons']['e2e'][0])

    def test_full_explicitly_runs_all_registered_checks_at_any_checkpoint(self):
        result = checks.plan(self.root, ['frontend/Form.svelte'], full=True, checkpoint='edit')
        self.assertEqual({c['id'] for c in result['checks']}, {'fast', 'e2e'})
        self.assertEqual(result['deferred_checks'], [])

    def test_invalid_checkpoint_or_registration_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'checkpoint'):
            checks.plan(self.root, [], checkpoint='typo')
        config = self.root / 'tools/harness/harness.toml'
        config.write_text(config.read_text().replace('"feature", "integration", "final"', '"featre"'))
        with self.assertRaisesRegex(ValueError, 'run_at'):
            checks.plan(self.root, [])
