"""Recorded evaluations keep missing cases and self-review limitations visible."""
import unittest

from _support import SOURCE
from test_evidence import EvidenceFixture
from harness import evidence, evaluation, pilot, provenance as p


class EvaluationTests(EvidenceFixture):
    def test_six_work_type_pilot_executes_real_red_green_and_experiment(self):
        result = pilot.run(self.root)
        self.assertEqual((result['status'], result['cases'], result['passed']), ('passed', 6, 6))
        self.assertEqual(result['experiment']['additions']['improvement'], 270)
        self.assertEqual(result['evaluation_type'], 'fixture')
    def suite(self, **overrides):
        value = {'version': 1, 'evaluation_type': 'fixture', 'population': 'One synthetic persistence case',
                 'limitations': 'Deterministic tool test only.',
                 'cases': [{'id': 'save-read', 'kind': 'implement', 'task': 'unit'}]} | overrides
        p.atomic(self.root / 'suite.json', value)

    def test_complete_case_is_recorded_without_fabricating_usage(self):
        self.suite()
        self.attach()
        review = self.review()
        self.assertEqual(evidence.finish(self.root, 'unit', review=review, complete=True)['status'], 'passed')
        result = evaluation.run(self.root, 'suite.json', 'fixture')
        self.assertEqual(result['passed'], 1)
        self.assertIsNone(result['usage'])
        self.assertFalse(result['cases'][0]['review']['independent'])

    def test_missing_case_stays_in_denominator_and_invalidates_suite(self):
        self.suite(cases=[{'id': 'missing', 'kind': 'research', 'task': 'missing'}])
        result = evaluation.run(self.root, 'suite.json', 'missing')
        self.assertEqual((result['status'], result['total'], result['passed']), ('failed', 1, 0))

    def test_self_review_cannot_be_labelled_independent_benchmark(self):
        self.suite(evaluation_type='agent_benchmark')
        self.attach()
        review = self.review()
        evidence.finish(self.root, 'unit', review=review, complete=True)
        result = evaluation.run(self.root, 'suite.json', 'self-review')
        self.assertEqual(result['status'], 'failed')
        self.assertIn('independent', result['cases'][0]['errors'][0])

    def test_same_task_cannot_inflate_the_sample_count(self):
        self.suite(cases=[{'id': 'first', 'kind': 'implement', 'task': 'unit'},
                          {'id': 'duplicate', 'kind': 'implement', 'task': 'unit'}])
        with self.assertRaisesRegex(ValueError, 'unique'):
            evaluation.run(self.root, 'suite.json', 'duplicates')
