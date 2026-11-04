"""Dataset questions select analysis; ordinary configuration edits do not."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from _support import SOURCE
from harness import context, evidence, skill_flows as flow, tasks

REF = '.agents/skills/research/references/data-analysis.md'


class DataAnalysisSelectionTests(unittest.TestCase):
    def test_dataset_topics_load_the_actual_method_document(self):
        for topic in ['data-analysis', 'dataset-analysis', 'eda', 'data-quality']:
            with self.subTest(topic=topic):
                result = context.select(SOURCE, 'review', [], [topic], read=True)
                selected = {row['path']: row for row in result['documents']}
                self.assertIn('.agents/skills/research/SKILL.md', selected)
                self.assertIn(REF, selected)
                self.assertTrue(selected[REF].get('content'))

    def test_ordinary_json_and_other_research_do_not_load_analysis_procedures(self):
        for kind, paths, topics in [('implement', ['backend/config.json'], []),
                                    ('plan', ['package.json'], []),
                                    ('research', ['docs/tasks/sample/task.json'], []),
                                    ('research', [], ['retrieval'])]:
            with self.subTest(kind=kind, paths=paths, topics=topics):
                result = context.select(SOURCE, kind, paths, topics, read=True)
                self.assertNotIn(REF, {row['path'] for row in result['documents']})


class DataAnalysisFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='data-analysis-flow-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        shutil.copytree(SOURCE / '.agents', self.root / '.agents')
        (self.root / 'AGENTS.md').write_text('Synthetic local analysis fixture only.\n')
        config = self.root / 'tools/harness/harness.toml'
        config.parent.mkdir(parents=True)
        config.write_text('version=1\n')
        tp = tasks.create(self.root, 'sample', 'review', 'Inspect empty synthetic JSON without inventing a rate', ['Report no evidence for an estimated rate'])
        task = json.loads(tp.read_text())
        task['acceptance'][0]['method'] = 'Observe empty input, method selection and real route movement'
        tp.write_text(json.dumps(task))
        data = self.root / '.runtime/input.json'
        data.write_text('[]\n')
        count = len(json.loads(data.read_text()))
        observed = self.root / '.runtime/observed.md'
        observed.write_text(f'Observed {count} records. No denominator exists; do not estimate a rate or claim no difference.\n')
        evidence.add(self.root, 'sample', 'OBSERVED', 'artifact', '.runtime/observed.md', 'A1',
                     task['acceptance'][0]['method'], 'Actual empty-input observation, not an agent-quality benchmark')

    def act(self, action, **kwargs):
        result = flow.act(self.root, 'analysis', action, **kwargs)
        self.assertFalse(result['stale'])
        return result

    def steps(self):
        for step in ['scope', 'execute', 'inspect']:
            self.act('step', step=step, evidence_ids=['OBSERVED'])

    def test_plan_calls_analysis_reads_its_method_and_resumes_parent(self):
        flow.start(self.root, 'analysis', 'sample', 'plan-project:plan')
        self.act('step', step='scope', evidence_ids=['OBSERVED'])
        result = self.act('move', edge_id='plan-data-analysis', reason='The request needs a dataset analysis')
        self.assertEqual(result['node'], 'research:analyze-data')
        selected = flow.selected_context(self.root, 'analysis', read_contents=True)
        self.assertTrue(any(d['path'] == REF and d.get('content') for d in selected['documents']))
        self.steps()
        self.act('validate', result='passed', evidence_ids=['OBSERVED'],
                 reason='Observed the actual empty dataset; no percentage or difference conclusion is supported')
        result = self.act('finish')
        self.assertEqual(result['node'], 'plan-project:plan')
        self.assertEqual(result['completed_steps'], ['scope'])

    def test_analysis_cannot_report_success_without_bound_observations(self):
        flow.start(self.root, 'analysis', 'sample', 'research:analyze-data')
        self.steps()
        with self.assertRaisesRegex(ValueError, 'existing task evidence'):
            self.act('validate', result='passed', reason='No observation was bound')
        self.act('move', edge_id='data-analysis-review', reason='Review the supported empty-input conclusion')
        self.assertEqual(flow.inspect(self.root, 'analysis')['node'], 'verify-work:inspect')


if __name__ == '__main__':
    unittest.main()
