"""Real subprocess metrics: failures, comparability, tampering and fixed trials."""
import json
from pathlib import Path
import tempfile
import unittest

from _support import SOURCE
from harness import experiments, provenance as p


def fixture_protocol(root: Path) -> dict:
    (root / 'input.json').write_text('[1,2,3]')
    (root / 'measure.py').write_text('''import json, sys
from pathlib import Path
values=json.loads(Path('input.json').read_text())
score=sum(values) + int(sys.argv[2])
Path(sys.argv[1]).write_text(json.dumps({'metrics':{'score':{'value':score,'unit':'points'}}}))
''')
    protocol = {'version': 1, 'question': 'Does the explicit offset change the deterministic score?',
                'population': 'One synthetic input only', 'limitations': 'Runner fixture; not agent or service quality.',
                'evaluation_type': 'fixture', 'inputs': ['input.json'], 'baseline': 'baseline',
                'seeds': [11, 23], 'timeout': 3, 'budget_seconds': 10,
                'metrics': {'score': {'unit': 'points', 'direction': 'maximize', 'minimum': 0}},
                'variants': {name: {'parameters': {'offset': offset},
                                    'command': ['{python}', 'measure.py', '{metrics}', str(offset), '{seed}']}
                             for name, offset in [('baseline', 0), ('candidate', 1)]}}
    p.atomic(root / 'recipe.json', protocol)
    return protocol


class ExperimentTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='harness-experiment-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.protocol = fixture_protocol(self.root)

    def test_real_runs_compare_all_trials_and_emit_reproducible_records(self):
        a = experiments.run(self.root, 'recipe.json', 'baseline')
        b = experiments.run(self.root, 'recipe.json', 'candidate')
        result = experiments.compare(self.root, a['report'], b['report'])
        self.assertEqual(result['metrics']['score']['improvement'], 1)
        self.assertEqual(a['summary']['passed'], 2)
        self.assertEqual(a['summary']['metrics']['score']['median'], 6)
        self.assertFalse(result['product_accepted'])

    def test_changed_input_or_environment_cannot_be_compared(self):
        a = experiments.run(self.root, 'recipe.json', 'baseline')
        (self.root / 'input.json').write_text('[9]')
        b = experiments.run(self.root, 'recipe.json', 'candidate')
        with self.assertRaisesRegex(ValueError, 'incompatible'):
            experiments.compare(self.root, a['report'], b['report'])

    def test_failed_trials_remain_in_denominator_and_block_comparison(self):
        (self.root / 'measure.py').write_text('raise SystemExit(9)')
        result = experiments.run(self.root, 'recipe.json', 'baseline')
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['summary']['failed'], 2)
        self.assertEqual(result['summary']['attempted'], 2)
        with self.assertRaisesRegex(ValueError, 'passing'):
            experiments.verify_report(self.root, result)

    def test_wrong_units_nonfinite_missing_metrics_and_quality_failure_are_not_passes(self):
        samples = ['{"metrics":{"score":{"value":1,"unit":"seconds"}}}',
                   '{"metrics":{"score":{"value":NaN,"unit":"points"}}}',
                   '{"metrics":{}}', '{"metrics":{"score":{"value":-1,"unit":"points"}}}']
        for value in samples:
            with self.subTest(value=value):
                (self.root / 'measure.py').write_text('from pathlib import Path; import sys; Path(sys.argv[1]).write_text(' + repr(value) + ')')
                self.assertEqual(experiments.run(self.root, 'recipe.json', 'baseline')['status'], 'failed')

    def test_raw_metric_tampering_or_source_mutation_is_detected(self):
        result = experiments.run(self.root, 'recipe.json', 'baseline')
        name = next(k for k in result['trials'][0]['artifacts'] if k.endswith('metrics.json'))
        (self.root / name).write_text('{}')
        with self.assertRaisesRegex(ValueError, 'artifact changed'):
            experiments.verify_report(self.root, result)
        (self.root / 'measure.py').write_text("from pathlib import Path; Path('input.json').write_text('[]')")
        self.assertEqual(experiments.run(self.root, 'recipe.json', 'baseline')['status'], 'stale')

    def test_budgets_and_seeds_are_validated_before_commands_run(self):
        for key, value in [('seeds', []), ('seeds', [1, 1]), ('timeout', 0), ('budget_seconds', True)]:
            protocol = self.protocol | {key: value}
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                experiments.validate(self.root, protocol)

    def test_total_budget_preserves_not_run_trials_and_does_not_reuse_old_metrics(self):
        protocol = self.protocol | {'seeds': [1, 2, 3], 'timeout': 0.02, 'budget_seconds': 0.01}
        p.atomic(self.root / 'recipe.json', protocol)
        (self.root / 'measure.py').write_text('import time; time.sleep(0.1)')
        result = experiments.run(self.root, 'recipe.json', 'baseline')
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['summary']['attempted'], 3)
        self.assertGreaterEqual(result['summary']['not_run'], 2)
        self.assertEqual(result['summary']['passed'], 0)

    def test_imported_empty_trial_report_cannot_be_mislabelled_successful(self):
        result = experiments.run(self.root, 'recipe.json', 'baseline')
        result['protocol']['seeds'] = []
        result['protocol_digest'] = p.signature(result['protocol'])
        result['trials'] = []
        result['summary'] = experiments.summarize([], result['protocol']['metrics'])
        with self.assertRaisesRegex(ValueError, 'seeds'):
            experiments.verify_report(self.root, result)
