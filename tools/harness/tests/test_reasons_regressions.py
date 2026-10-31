"""Stable behavioral regressions; fixture schema may evolve without weakening cases."""
import unittest
import test_reasons as fixtures
from harness import provenance as p, skill_flows as flow


class ReadinessRegressionTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.ReadinessTests(methodName='runTest');self.f.setUp();self.addCleanup(self.f.doCleanups)

    def test_dependency_order_is_not_just_set_membership(self):
        f=self.f;f.meta['operations'][1]['depends_on']=['O1'];f.update_design();f.audit=f.review()
        f.audit['operations']=['O2','O1'];f.audit['coverage']={'A1':['O1','O2']};f.write_review()
        with self.assertRaises(ValueError):f.ready()

    def test_selected_work_keeps_its_fenced_example(self):
        f=self.f
        text=f.design_path.read_text().replace('### O1\n\nImplement','### O1\n\n```text\n### O2\nREQUIRED_O1_EXAMPLE\n```\n\nImplement')
        f.design_path.write_text(text);f.rehash('DESIGN');f.audit=f.review();f.write_review();f.start()
        result=flow.selected_context(f.root,'run',read_contents=True)
        selected=next(d for d in result['documents'] if d['path']=='.runtime/design.md')['content']
        self.assertIn('REQUIRED_O1_EXAMPLE',selected)
        self.assertNotIn('Independent later work.',selected)

    def test_decision_basis_cannot_be_retargeted_after_alignment(self):
        f=self.f;f.start();tp=f.root/'docs/tasks/demo/task.json';task=p.load(tp)
        (f.root/'.runtime/new-basis.md').write_text('Different authorized boundary')
        task['evidence']['E']['path']='.runtime/new-basis.md'
        task['evidence']['E']['sha256']=p.sha(f.root/'.runtime/new-basis.md');p.atomic(tp,task)
        self.assertTrue(flow.inspect(f.root,'run')['stale'])
        with self.assertRaises(ValueError):f.f.act('step',step='prepare',evidence_ids=['E'])
