"""Completion requires live, immutable evidence and a criterion-bound review."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from _support import SOURCE, fixture_verification
from harness import checks, context, evidence, provenance as p, tasks


class EvidenceFixture(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='harness-evidence-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.path = tasks.create(self.root, 'unit', 'implement', 'Persist a value', ['A saved value can be retrieved'])
        config = self.root / 'tools/harness/harness.toml'
        config.parent.mkdir(parents=True)
        (self.root / 'verify.py').write_text("from pathlib import Path\np=Path('.runtime/value'); p.write_text('saved'); assert p.read_text()=='saved'\n")
        config.write_text('version=1\n[[checks]]\nid="persistence"\ncommand=["{python}","verify.py"]\npaths=["**"]')

    def attach(self):
        report = checks.run(self.root, ['verify.py'])
        self.assertEqual(report['status'], 'passed', report)
        evidence.add(self.root, 'unit', 'E1', 'check', Path(report['report']).relative_to(self.root).as_posix(),
                     'A1', 'Run the persistence integration check', 'Writes a value and retrieves it', check='persistence')
        return report

    def review(self):
        result = evidence.review_template(self.root, 'unit')
        path = self.root / result['review']
        data = p.load(path)
        data['reviewer'] = 'Local regression reviewer'
        for criterion in data['criteria']:
            criterion.update(decision='passed', reason='Observed the saved value being read back in the linked integration check.')
        data['verification'] = fixture_verification(p.load(self.path))
        p.atomic(path, data)
        return result['review']


class EvidenceTests(EvidenceFixture):
    def test_complete_and_historical_record_survive_later_code_changes(self):
        self.attach()
        review = self.review()
        result = evidence.finish(self.root, 'unit', review=review, complete=True)
        self.assertEqual(result['status'], 'passed', result)
        self.assertEqual(tasks.validate(p.load(self.path), root=self.root, task_path=self.path), [])
        (self.root / 'verify.py').write_text('raise RuntimeError("new revision")')
        self.assertEqual(tasks.validate(p.load(self.path), root=self.root, task_path=self.path), [])
        self.assertEqual(evidence.finish(self.root, 'unit')['status'], 'needs_revision')

    def test_missing_and_escaped_evidence_are_rejected(self):
        for relative in ('missing.md', '../outside.md', '/tmp/outside.md'):
            with self.subTest(relative=relative), self.assertRaises((OSError, ValueError)):
                evidence.add(self.root, 'unit', 'E1', 'artifact', relative, 'A1', 'Inspect', 'Missing')

    def test_no_review_or_pending_review_cannot_close(self):
        self.attach()
        self.assertEqual(evidence.finish(self.root, 'unit', complete=True)['status'], 'needs_revision')
        evidence.review_template(self.root, 'unit')
        result = evidence.finish(self.root, 'unit', review='docs/tasks/unit/review.json', complete=True)
        self.assertEqual(result['status'], 'needs_revision')

    def test_source_change_or_tampered_log_blocks_closure(self):
        report = self.attach()
        review = self.review()
        Path(report['results'][0]['log']).write_text('tampered')
        self.assertEqual(evidence.finish(self.root, 'unit', review=review)['status'], 'needs_revision')

    def test_execute_permission_change_invalidates_current_evidence(self):
        self.attach()
        review = self.review()
        script = self.root / 'verify.py'
        script.chmod(script.stat().st_mode ^ 0o100)
        result = evidence.finish(self.root, 'unit', review=review)
        self.assertEqual(result['status'], 'needs_revision')
        self.assertIn('executable', result['errors'][0])

    def test_same_python_version_in_another_environment_cannot_borrow_evidence(self):
        self.attach()
        review = self.review()
        with patch('harness.provenance.sys.prefix', str(self.root / 'another-environment')):
            result = evidence.finish(self.root, 'unit', review=review)
        self.assertEqual(result['status'], 'needs_revision')
        self.assertIn('environment', result['errors'][0])

    def test_contract_change_requires_new_review(self):
        self.attach()
        review = self.review()
        task = p.load(self.path)
        task['acceptance'][0]['condition'] = 'A different, more demanding outcome'
        p.atomic(self.path, task)
        self.assertIn('stale', evidence.finish(self.root, 'unit', review=review)['errors'][0])

    def test_artifact_alone_does_not_prove_implementation(self):
        (self.root / 'result.md').write_text('I think it works')
        evidence.add(self.root, 'unit', 'E1', 'artifact', 'result.md', 'A1', 'Read result', 'Claim only')
        self.assertIn('work-type', evidence.finish(self.root, 'unit')['errors'][0])

    def test_nonbehavioral_check_cannot_be_named_as_implementation_evidence(self):
        config = self.root / 'tools/harness/harness.toml'
        config.write_text(config.read_text() + '\ncovers_behavior=false\n[[checks]]\nid="actual-behavior"\ncommand=["{python}","verify.py"]\npaths=["**"]\n')
        report = checks.run(self.root, ['verify.py'])
        self.assertEqual(report['status'], 'passed')
        relative = Path(report['report']).relative_to(self.root).as_posix()
        with self.assertRaisesRegex(ValueError, 'behavior'):
            evidence.add(self.root, 'unit', 'E1', 'check', relative, 'A1', 'Check persistence',
                         'Static diagnostic is insufficient', check='persistence')
        evidence.add(self.root, 'unit', 'E1', 'check', relative, 'A1', 'Run persistence',
                     'Observed persistence behavior', check='actual-behavior')

    def test_all_conditions_need_their_own_review_and_evidence(self):
        self.attach()
        task = p.load(self.path)
        task['acceptance'].append({'id': 'A2', 'condition': 'Reject invalid input', 'method': '', 'status': 'pending', 'evidence': []})
        p.atomic(self.path, task)
        review = self.review()
        self.assertEqual(evidence.finish(self.root, 'unit', review=review)['status'], 'needs_revision')

    def test_missing_private_history_is_explicit_and_does_not_hide_shared_artifact_tampering(self):
        report = self.attach()
        (self.root / 'result.md').write_text('Observed persistence requirement')
        evidence.add(self.root, 'unit', 'A1', 'artifact', 'result.md', 'A1', 'Inspect result', 'Persistence conclusion')
        # This public artifact was added after the old run; obtain fresh check evidence.
        task = p.load(self.path)
        task['evidence'].pop('E1')
        task['acceptance'][0]['evidence'].remove('E1')
        p.atomic(self.path, task)
        report = self.attach()
        review = self.review()
        self.assertEqual(evidence.finish(self.root, 'unit', review=review, complete=True)['status'], 'passed')
        Path(report['report']).unlink()
        data = p.load(self.path)
        self.assertTrue(tasks.validate(data, root=self.root, task_path=self.path))
        self.assertEqual(tasks.validate(data, root=self.root, task_path=self.path, allow_missing_runtime=True), [])
        (self.root / 'result.md').write_text('Changed conclusion')
        self.assertTrue(tasks.validate(data, root=self.root, task_path=self.path, allow_missing_runtime=True))

    def test_design_kind_routes_architecture_and_ui_is_opt_in(self):
        selected = context.select(SOURCE, 'design', [], [], read=False)
        paths = [x['path'] for x in selected['documents']]
        self.assertIn('.agents/skills/plan-project/references/quality-requirements.md', paths)
        self.assertNotIn('.agents/skills/design-first/SKILL.md', paths)
        selected = context.select(SOURCE, 'design', [], ['ui'], read=False)
        self.assertIn('.agents/skills/design-first/SKILL.md', [x['path'] for x in selected['documents']])
