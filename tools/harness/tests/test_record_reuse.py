"""Real cache/closure/flow behavior after unrelated records versus actual inputs."""
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

import test_skill_flows as flow_fixture
from harness import checks, evidence, provenance as p, skill_flows, tasks
from _support import fixture_verification


class RecordReuseTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='record-reuse-')
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.tp = tasks.create(self.root, 'unit', 'implement', 'Persist a value', ['Read the saved value'])
        self.config = self.root / 'tools/harness/harness.toml'
        self.config.parent.mkdir(parents=True)
        self.config.write_text('version=1\n[[checks]]\nid="python"\ncommand=["{python}","verify.py"]\n'
                               'paths=["verify.py"]\ncacheable=true\nignore_task_records=true\n')
        (self.root / 'verify.py').write_text("from pathlib import Path\np=Path('.runtime/count'); p.parent.mkdir(exist_ok=True); p.write_text(str(int(p.read_text())+1) if p.exists() else '1')\n")

    def run_check(self):
        result = checks.run(self.root, ['verify.py'], reuse=True)
        self.assertEqual(result['status'], 'passed', result)
        return result

    def unrelated(self):
        folder = tasks.create(self.root, 'other', 'review', 'Independent work', ['Inspect independent result']).parent
        (folder / 'request.md').write_text('Independent request.\n')
        (folder / 'notes.md').write_text('Another session progress.\n')
        return folder

    def attach(self):
        result = self.run_check()
        evidence.add(self.root, 'unit', 'E', 'check', Path(result['report']).relative_to(self.root).as_posix(),
                     'A1', 'Execute actual persistence', 'Observed file behavior', check='python')
        review = evidence.review_template(self.root, 'unit')['review']
        data = p.load(self.root / review);data['reviewer'] = 'Self-review fixture'
        for row in data['criteria']:row.update(decision='passed', reason='Observed the actual file operation.')
        data['verification'] = fixture_verification(p.load(self.tp));p.atomic(self.root / review, data)
        return result, review

    def test_unrelated_new_task_reuses_behavior_result(self):
        first = self.run_check();self.unrelated();second = self.run_check()
        self.assertTrue(second['results'][0]['reused'])
        self.assertEqual((self.root / '.runtime/count').read_text(), '1')
        self.assertNotEqual(first['source_snapshot'], second['source_snapshot'])

    def test_unrelated_new_task_does_not_block_closure(self):
        _, review = self.attach();self.unrelated()
        result = evidence.finish(self.root, 'unit', review=review)
        self.assertEqual(result['status'], 'passed', result)

    def test_unrelated_new_task_does_not_invalidate_flow(self):
        fixture = flow_fixture.FlowTests(methodName='runTest');fixture.setUp();self.addCleanup(fixture.doCleanups)
        config = fixture.root / 'tools/harness/harness.toml'
        config.write_text(config.read_text().replace('paths=["**"]', 'paths=["example.py"]\nignore_task_records=true'))
        fixture.start();fixture.verified_parent()
        tasks.create(fixture.root, 'other', 'review', 'Independent work', ['Independent result'])
        result = skill_flows.inspect(fixture.root, 'run')
        self.assertEqual(result['stale'], [], result)
        self.assertEqual(fixture.act('move', edge_id='done')['node'], 'docs:index')

    def test_unknown_check_keeps_conservative_cache(self):
        self.config.write_text(self.config.read_text().replace('ignore_task_records=true', 'ignore_task_records=false'))
        self.run_check();self.unrelated()
        self.assertFalse(self.run_check()['results'][0]['reused'])

    def test_declared_record_input_is_not_ignored(self):
        folder = self.unrelated()
        self.config.write_text(self.config.read_text().replace('paths=["verify.py"]', 'paths=["verify.py","docs/tasks/other/notes.md"]'))
        self.run_check();(folder / 'notes.md').write_text('Changed required fixture.\n')
        self.assertFalse(self.run_check()['results'][0]['reused'])

    def test_task_input_record_change_blocks_closure(self):
        folder = self.unrelated();task=p.load(self.tp);task['inputs']=['docs/tasks/other/notes.md'];p.atomic(self.tp,task)
        _, review = self.attach();(folder / 'notes.md').write_text('Changed requirement.\n')
        self.assertEqual(evidence.finish(self.root, 'unit', review=review)['status'], 'needs_revision')

    def test_code_config_project_docs_permissions_and_environment_still_invalidate(self):
        for relative in ['verify.py','tools/harness/harness.toml','docs/demo/features/login/spec.md','docs/tasks/other/helper.py']:
            with self.subTest(relative=relative):
                self.run_check();file=self.root/relative;file.parent.mkdir(parents=True,exist_ok=True)
                if file.suffix=='.toml' or relative=='verify.py':file.write_text(file.read_text()+'\n# changed input\n')
                else:file.write_text('# New actual source\n')
                self.assertFalse(self.run_check()['results'][0]['reused'])
        self.run_check();file=self.root/'verify.py';file.chmod(file.stat().st_mode ^ 0o100)
        self.assertFalse(self.run_check()['results'][0]['reused'])
        with patch.dict('os.environ', {'HARNESS_RECORD_TEST':'new-condition'}):
            self.assertFalse(self.run_check()['results'][0]['reused'])

    def test_legacy_report_keeps_full_source_comparison(self):
        result, _ = self.attach();report=p.load(Path(result['report']));report.pop('verification_policy',None)
        self.unrelated()
        with self.assertRaisesRegex(ValueError, 'source snapshot'):
            evidence.current_sources(self.root,report,self.tp)


if __name__ == '__main__':
    unittest.main()
