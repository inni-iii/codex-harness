"""Finding updates preserve intent readiness while completion stays strict."""
from pathlib import Path
import unittest

import test_reasons as fixtures
import test_evidence as evidence_fixtures
from harness import evidence, provenance as p, reasons, skill_flows as flow


class IntentContractTests(unittest.TestCase):
    def fixture(self):
        f=fixtures.ReadinessTests(methodName='runTest');f.setUp();self.addCleanup(f.doCleanups)
        self.native_alignment(f,'initial')
        return f

    def native_alignment(self,f,name):
        relative='.runtime/'+name+'-alignment.json'
        reasons.alignment_template(f.root,f.task(),f.root/'docs/tasks/demo/task.json','DESIGN',['O1'],relative,['E'])
        f.audit=p.load(f.root/relative)
        f.audit.update(reviewer={'name':'Fixture self review','type':'agent','independent':False},decision='ready',reason='Current approved intent and operation are aligned.')
        f.write_review()

    def finding(self,f):
        tp=f.root/'docs/tasks/demo/task.json';task=p.load(tp);task['findings'].append('F1');p.atomic(tp,task)

    def test_generated_alignment_survives_finding_append(self):
        f=self.fixture();before=(f.root/'.runtime/alignment.json').read_bytes()
        self.finding(f)
        self.assertEqual(f.ready()['operations'],['O1'])
        self.assertEqual((f.root/'.runtime/alignment.json').read_bytes(),before)

    def test_flow_preserves_validated_steps_and_progress_after_finding_append(self):
        f=self.fixture();f.start();f.f.verified_parent()
        progress=flow.progress(f.root,f.task(),f.root/'docs/tasks/demo/task.json')
        before=p.load(flow.path(f.root,'run'));self.finding(f)
        result=flow.inspect(f.root,'run')
        self.assertEqual(result['stale'],[],result)
        self.assertEqual(result['completed_steps'],['prepare','perform'])
        self.assertEqual(flow.progress(f.root,f.task(),f.root/'docs/tasks/demo/task.json'),progress)
        self.assertEqual(p.load(flow.path(f.root,'run'))['revision'],before['revision'])
        self.assertEqual(f.f.act('move',edge_id='done')['node'],'docs:index')

    def test_real_intent_changes_still_require_alignment_and_restart(self):
        changes={'goal':'Different goal','kind':'debug','scope':['outside.py'],'constraints':['New accepted boundary'],
                 'inputs':['.runtime/output.md'],'depends_on':['other']}
        for key,value in changes.items():
            with self.subTest(field=key):
                f=self.fixture();f.start();tp=f.root/'docs/tasks/demo/task.json';task=p.load(tp);task[key]=value;p.atomic(tp,task)
                with self.assertRaises(ValueError):f.ready()
                self.assertTrue(flow.inspect(f.root,'run')['stale'])
        for key,value in [('condition','Different required outcome'),('method','Different verification contract')]:
            with self.subTest(criterion=key):
                f=self.fixture();f.start();tp=f.root/'docs/tasks/demo/task.json';task=p.load(tp);task['acceptance'][0][key]=value;p.atomic(tp,task)
                with self.assertRaises(ValueError):f.ready()
                self.assertTrue(flow.inspect(f.root,'run')['stale'])

    def test_design_and_bound_decision_changes_still_require_alignment(self):
        for ident in ['DESIGN','E']:
            with self.subTest(evidence=ident):
                f=self.fixture();entry=f.task()['evidence'][ident]
                with (f.root/entry['path']).open('a') as out:out.write('\nChanged accepted contract or decision.\n')
                f.rehash(ident)
                with self.assertRaises(ValueError):f.ready()

    def test_new_finding_invalidates_old_completion_review_and_cannot_be_omitted(self):
        f=evidence_fixtures.EvidenceFixture(methodName='runTest');f.setUp();self.addCleanup(f.doCleanups)
        f.attach();review=f.review();task=p.load(f.path);before=evidence.contract(task)
        task['findings'].append('F1');p.atomic(f.path,task)
        self.assertNotEqual(before,evidence.contract(task))
        self.assertEqual(evidence.finish(f.root,'unit',review=review)['status'],'needs_revision')
        audit=p.load(f.root/review);audit['task_contract']=evidence.contract(task);p.atomic(f.root/review,audit)
        result=evidence.finish(f.root,'unit',review=review)
        self.assertEqual(result['status'],'needs_revision')
        self.assertTrue(any('finding' in error for error in result['errors']),result)

    def test_legacy_alignment_keeps_original_full_contract_semantics(self):
        f=self.fixture();f.audit['version']=1;f.audit['task_contract']=evidence.contract(f.task());f.write_review()
        self.assertEqual(f.ready()['operations'],['O1'])
        original=(f.root/'.runtime/alignment.json').read_bytes();self.finding(f)
        with self.assertRaises(ValueError):f.ready()
        self.assertEqual((f.root/'.runtime/alignment.json').read_bytes(),original)

    def test_legacy_flow_is_preserved_until_explicit_restart_upgrade(self):
        f=self.fixture();f.start();path=flow.path(f.root,'run');state=p.load(path)
        state['version']=1;state['contract']=evidence.contract(f.task());state['current']['inputs']['request']=evidence.contract(f.task())
        state.pop('integrity');state['integrity']=p.signature(state);p.atomic(path,state)
        before=path.read_bytes();self.finding(f)
        self.assertTrue(flow.inspect(f.root,'run')['stale']);self.assertEqual(path.read_bytes(),before)
        self.native_alignment(f,'upgrade')
        f.f.act('restart',inputs={'design':'DESIGN','alignment':'ALIGN'},reason='Explicitly upgrade to the current approved intent binding')
        upgraded=p.load(path);self.assertEqual(upgraded['version'],2)
        self.assertEqual(upgraded['events'][0],state['events'][0])
        self.assertEqual(flow.inspect(f.root,'run')['stale'],[])

    def test_source_change_and_unknown_alignment_version_remain_rejected(self):
        f=self.fixture();f.start();f.f.verified_parent();(f.root/'example.py').write_text('changed actual source')
        self.assertTrue(flow.inspect(f.root,'run')['stale'])
        f=self.fixture();f.audit['version']=99;f.write_review()
        with self.assertRaises(ValueError):f.ready()


if __name__ == '__main__':
    unittest.main()
