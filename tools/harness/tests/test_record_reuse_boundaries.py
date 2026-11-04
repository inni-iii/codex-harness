"""Input protection and uncached record inspection around opt-in reuse."""
from pathlib import Path
import unittest

import test_record_reuse as fixture
import test_skill_flows as flow_fixture
from harness import checks, evidence, provenance as p, skill_flows, tasks
from _support import fixture_security


class RecordBoundaries(unittest.TestCase):
    def setUp(self):
        self.f = fixture.RecordReuseTests(methodName='runTest');self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.root = self.f.root

    def test_static_record_check_still_runs_and_blocks_invalid_record(self):
        script=self.root/'inspect_records.py'
        script.write_text("from pathlib import Path\nassert not any('INVALID' in p.read_text() for p in Path('docs/tasks').rglob('notes.md'))\n")
        self.f.config.write_text(self.f.config.read_text()+'\n[[checks]]\nid="records"\ncommand=["{python}","inspect_records.py"]\npaths=["**"]\ncovers_behavior=false\ncacheable=false\n')
        self.f.run_check();folder=self.f.unrelated();(folder/'notes.md').write_text('INVALID')
        result=checks.run(self.root,['verify.py'],reuse=True)
        self.assertEqual(result['status'],'failed')
        self.assertTrue(result['results'][0]['reused'])
        self.assertFalse(result['results'][1]['reused'])
        self.assertEqual(result['results'][1]['status'],'failed')

    def test_workflow_record_reference_invalidates_cached_behavior(self):
        self.f.unrelated();profile=self.root/'docs/demo/workflow.toml';profile.parent.mkdir(parents=True)
        profile.write_text('version=1\nname="demo"\nstate="active"\n'
                           '[[checks]]\nid="project"\ncommand=["{python}","verify.py"]\npaths=["verify.py"]\nignore_task_records=true\ncacheable=true\n'
                           '[context]\ndocuments=["docs/tasks/other/notes.md"]\n' + fixture_security(self.root, 'docs/demo'))
        first=checks.run(self.root,['verify.py'],workflow='docs/demo/workflow.toml',reuse=True)
        self.assertEqual(first['status'],'passed',first)
        (self.root/'docs/tasks/other/notes.md').write_text('Changed workflow input')
        second=checks.run(self.root,['verify.py'],workflow='docs/demo/workflow.toml',reuse=True)
        self.assertEqual(second['status'],'passed',second)
        self.assertTrue(all(not r['reused'] for r in second['results']))

    def test_task_scope_and_dependency_and_artifact_records_are_protected(self):
        folder=self.f.unrelated();task=p.load(self.f.tp)
        task['scope']=['docs/tasks/other/**'];task['depends_on']=['other'];p.atomic(self.f.tp,task)
        evidence.add(self.root,'unit','INPUT','artifact','docs/tasks/other/notes.md','A1','Compare dependency input','Observed source requirement')
        result,_=self.f.attach();report=p.load(Path(result['report']))
        (folder/'notes.md').write_text('Changed dependency source')
        with self.assertRaisesRegex(ValueError,'source snapshot'):
            evidence.current_sources(self.root,report,self.f.tp)

    def test_declared_flow_input_record_change_invalidates_validation(self):
        f=flow_fixture.FlowTests(methodName='runTest');f.setUp();self.addCleanup(f.doCleanups)
        config=f.root/'tools/harness/harness.toml';config.write_text(config.read_text().replace('paths=["**"]','paths=["example.py"]\nignore_task_records=true'))
        other=tasks.create(f.root,'other','review','Independent work',['Independent result']).parent
        tp=f.root/'docs/tasks/demo/task.json';task=p.load(tp);task['inputs']=['docs/tasks/other/notes.md'];p.atomic(tp,task)
        f.start();f.verified_parent();(other/'notes.md').write_text('Changed required source')
        self.assertTrue(skill_flows.inspect(f.root,'run')['stale'])

    def test_arbitrary_task_json_and_unknown_policy_are_not_bypasses(self):
        result=self.f.run_check();file=self.root/'docs/tasks/fixture.json';file.write_text('{"actual_input":1}')
        self.assertFalse(self.f.run_check()['results'][0]['reused'])
        report=p.load(Path(result['report']));report['verification_policy']['version']=99
        with self.assertRaisesRegex(ValueError,'policy'):
            evidence.current_sources(self.root,report,self.f.tp)

    def test_invalid_declaration_and_broad_record_input_remain_conservative(self):
        config=self.f.config.read_text();self.f.config.write_text(config.replace('ignore_task_records=true','ignore_task_records="true"'))
        with self.assertRaisesRegex(ValueError,'ignore_task_records'):
            checks.run(self.root,['verify.py'])
        self.f.config.write_text(config.replace('paths=["verify.py"]','paths=["**"]'))
        self.f.run_check();self.f.unrelated()
        self.assertFalse(self.f.run_check()['results'][0]['reused'])


if __name__ == '__main__':
    unittest.main()
