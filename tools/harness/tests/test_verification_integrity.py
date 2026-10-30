"""Counterexamples for corrupted reuse, mutable completion and trial provenance."""
import copy
from pathlib import Path
import unittest
from unittest.mock import patch

from _support import SOURCE
from test_harness import Workspace
from test_evidence import EvidenceFixture
from test_experiments import fixture_protocol
from harness import checks, evidence, experiments, provenance as p


class CacheIntegrityTests(Workspace):
    def test_valid_json_with_wrong_cache_shape_is_ignored(self):
        self.probe()
        for malformed in ([], None, True, 'wrong shape'):
            p.atomic(self.root / '.runtime/check-cache.json', malformed)
            result = checks.run(self.root, ['probe.py'], reuse=True)
            self.assertEqual(result['status'], 'passed')
            self.assertFalse(result['results'][0]['reused'])

    def test_malformed_or_contradictory_cache_entry_is_rerun(self):
        self.config(summary='unittest')
        self.probe("print('Ran 1 test in 0.001s\\nOK')")
        for update in (None, {'exit_code': 7}, {'test_count': 0}, {'failed_count': 1},
                       {'execution_error': 'timeout'}, {'summary_error': 'invalid'}, {'covers_behavior': False}):
            checks.run(self.root, ['probe.py'])
            cache_path = self.root / '.runtime/check-cache.json'
            cache = p.load(cache_path)
            key = next(iter(cache))
            cache[key] = [] if update is None else cache[key] | update
            p.atomic(cache_path, cache)
            result = checks.run(self.root, ['probe.py'], reuse=True)
            with self.subTest(update=update):
                self.assertEqual(result['status'], 'passed')
                self.assertFalse(result['results'][0]['reused'])

    def test_cache_rechecks_raw_summary_instead_of_trusting_its_pass_label(self):
        self.config(summary='unittest')
        self.probe("print('Ran 1 test in 0.001s\\nOK')")
        checks.run(self.root, ['probe.py'])
        cache_path = self.root / '.runtime/check-cache.json'
        cache = p.load(cache_path)
        record = next(iter(cache.values()))
        Path(record['log']).write_text('Ran 0 tests in 0.001s\nOK\n')
        record['log_sha256'] = p.sha(Path(record['log']))
        p.atomic(cache_path, cache)
        result = checks.run(self.root, ['probe.py'], reuse=True)
        self.assertFalse(result['results'][0]['reused'])
        self.assertEqual(result['results'][0]['test_count'], 1)


class CompletionIntegrityTests(EvidenceFixture):
    def test_contradictory_report_cannot_be_attached_as_completion_evidence(self):
        (self.root / 'verify.py').write_text("print('Ran 1 test in 0.001s\\nOK')")
        config = self.root / 'tools/harness/harness.toml'
        config.write_text(config.read_text() + '\ntest_summary="unittest"\n')
        report = checks.run(self.root, ['verify.py'])
        path = Path(report['report'])
        data = p.load(path)
        data['results'][0]['failed_count'] = 1
        p.atomic(path, data)
        with self.assertRaisesRegex(ValueError, 'result|summary|report'):
            evidence.add(self.root, 'unit', 'E1', 'check', path.relative_to(self.root).as_posix(),
                         'A1', 'Verify persistence', 'Contradictory record', check='persistence')

    def test_finish_preserves_task_edited_during_assessment(self):
        self.attach()
        review = self.review()
        assess = evidence.assess
        def concurrent_edit(*args, **kwargs):
            result = assess(*args, **kwargs)
            current = p.load(self.path)
            current['goal'] = 'New user requirement from another session'
            p.atomic(self.path, current)
            return result
        with patch('harness.evidence.assess', side_effect=concurrent_edit):
            result = evidence.finish(self.root, 'unit', review=review, complete=True)
        self.assertEqual(result['status'], 'needs_revision')
        self.assertEqual(p.load(self.path)['goal'], 'New user requirement from another session')
        self.assertNotEqual(p.load(self.path)['status'], 'complete')

    def test_finish_does_not_bind_a_review_changed_after_validation(self):
        self.attach()
        review = self.review()
        assess = evidence.assess
        def concurrent_edit(*args, **kwargs):
            result = assess(*args, **kwargs)
            current = p.load(self.root / review)
            current['criteria'][0]['decision'] = 'failed'
            p.atomic(self.root / review, current)
            return result
        with patch('harness.evidence.assess', side_effect=concurrent_edit):
            result = evidence.finish(self.root, 'unit', review=review, complete=True)
        self.assertEqual(result['status'], 'needs_revision')
        self.assertNotEqual(p.load(self.path)['status'], 'complete')

    def test_attach_does_not_overwrite_a_concurrent_task_edit(self):
        report = checks.run(self.root, ['verify.py'])
        verify = evidence.verify_entry
        def concurrent_edit(*args, **kwargs):
            verify(*args, **kwargs)
            current = p.load(self.path)
            current['goal'] = 'Concurrent requirement'
            p.atomic(self.path, current)
        with patch('harness.evidence.verify_entry', side_effect=concurrent_edit), self.assertRaisesRegex(ValueError, 'changed'):
            evidence.add(self.root, 'unit', 'E1', 'check', Path(report['report']).relative_to(self.root).as_posix(),
                         'A1', 'Verify persistence', 'Real check', check='persistence')
        self.assertEqual(p.load(self.path)['goal'], 'Concurrent requirement')


class ExperimentIntegrityTests(Workspace):
    def test_malformed_reports_are_rejected_with_a_structured_validation_error(self):
        fixture_protocol(self.root)
        original = experiments.run(self.root, 'recipe.json', 'baseline')
        for update in ({'trials': None}, {'protocol': None}, {'trials': [{}]}):
            with self.subTest(update=update), self.assertRaises(ValueError):
                experiments.verify_report(self.root, original | update)
        report = copy.deepcopy(original)
        report['trials'][0]['execution']['exit_code'] = False
        with self.assertRaises(ValueError):
            experiments.verify_report(self.root, report)

    def test_repeated_trials_need_distinct_raw_files_and_matching_commands(self):
        fixture_protocol(self.root)
        original = experiments.run(self.root, 'recipe.json', 'baseline')
        for problem in ('duplicate-artifacts', 'duplicate-index', 'missing-log', 'wrong-command', 'missing-input-binding'):
            report = copy.deepcopy(original)
            if problem == 'duplicate-artifacts':
                report['trials'][1]['artifacts'] = report['trials'][0]['artifacts'].copy()
            elif problem == 'duplicate-index':
                report['trials'][1]['trial'] = 0
            elif problem == 'missing-log':
                row = report['trials'][0]
                row['artifacts'] = {k:v for k,v in row['artifacts'].items() if not k.endswith('/output.log')}
            elif problem == 'wrong-command':
                report['trials'][0]['command'] = ['invented-command']
            else:
                report['inputs'] = {}
            with self.subTest(problem=problem), self.assertRaises(ValueError):
                experiments.verify_report(self.root, report)
