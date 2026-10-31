"""A synthetic feature starts only after design and completes a real check/doc loop."""
from pathlib import Path
import json
import shutil
import tempfile
import unittest

from _support import SOURCE
from harness import checks, core, evidence, flow_catalog, provenance as p, reasons, skill_flows as flow, skills, tasks
import test_skill_flows as fixtures


class AuthoringCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.FlowTests(methodName='runTest');self.f.setUp();self.addCleanup(self.f.doCleanups)

    def test_new_implementation_skill_has_readiness_inputs(self):
        skills.create(self.f.root,'edit-result','Edit the scoped result','Read current intent and update the scoped result.',kinds=['implement'])
        node=flow_catalog.load(self.f.root)['nodes']['edit-result:main']
        self.assertEqual(node['entry_checks'],['alignment']);self.assertEqual(set(node['inputs']),{'request','design','alignment'})
        with self.assertRaises(ValueError):flow.start(self.f.root,'new','demo','edit-result:main')

    def test_old_custom_named_input_without_role_is_not_reinterpreted_as_reasons(self):
        self.f.routes['work'][1]['inputs']=['request','design']
        fixtures.dump_routes(self.f.root/'.agents/skills/work/routes.toml',self.f.routes['work'])
        flow.start(self.f.root,'run','demo','work:main');self.f.act('move',edge_id='side',reason='A legacy generic input',inputs={'design':'E'})
        self.assertEqual(flow.selected_context(self.f.root,'run',read_contents=True)['node'],'work:next')


class ForwardFeatureTests(unittest.TestCase):
    def test_design_precedes_code_and_real_feature_check_returns_through_docs(self):
        with tempfile.TemporaryDirectory(prefix='reasons-forward-') as directory:
            root=Path(directory).resolve()
            for source in core.files(SOURCE):
                dest=root/source.relative_to(SOURCE);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
            (root/'tools/harness/harness.toml').write_text('version=1\n[[checks]]\nid="python"\ncommand=["{python}","-m","unittest","discover","-s","tests","-v"]\npaths=["**"]\ntest_summary="unittest"\ntimeout=30\n')
            tp=tasks.create(root,'forward-feature','implement','Known-answer fixture: only owners may edit notes',['Owner can edit','Non-owner is rejected without mutation','Missing note is distinguished'])
            task=p.load(tp);task['scope']=['backend/note.py','tests/test_note.py']
            for c in task['acceptance']:c['method']='Execute the known-answer note behavior fixture'
            p.atomic(tp,task)
            with self.assertRaises(ValueError):flow.start(root,'feature','forward-feature','python-backend:implement')
            self.assertFalse((root/'backend/note.py').exists())
            (root/'.runtime').mkdir(exist_ok=True)
            (root/'.runtime/request.md').write_text('Authored fixture request: owner edits succeed; another actor is rejected without mutation; missing notes are distinguished. This is a test input, not a real user approval.')
            evidence.add(root,'forward-feature','REQUEST','artifact','.runtime/request.md','A1','Execute the known-answer note behavior fixture','Known-answer fixture requirement')
            metadata={'version':1,'kind':'reasons-design','profile':'behavioral','requirements':['R1'],
                      'operations':[{'id':'O1','requirements':['R1'],'paths':['backend/note.py','tests/test_note.py'],'depends_on':[],'verification':'Actual owner/non-owner/missing tests; preserve the input note on rejection'}],
                      'decisions':[],'references':[]}
            parts=['# Authored note fixture design','```json',json.dumps(metadata),'```']
            contents={'requirements':'R1: only owners can edit; preserve the supplied record on rejection.',
                      'entities':'A note has an owner and text; actor identity is provided by this pure fixture boundary.',
                      'approach':'Reuse a pure function and explicit existing Python exceptions; no service/framework/DB.',
                      'structure':'backend/note.py implements the pure rule. tests/test_note.py observes outputs and input preservation.',
                      'operations':'### O1\nImplement edit_note and the three accepted boundary tests.',
                      'norms':'Use existing Python conventions and local unittest; no remote/network execution.',
                      'safeguards':'Missing record raises LookupError; non-owner raises PermissionError; do not mutate inputs or add unrelated features.'}
            for name in reasons.SECTIONS:parts.extend(['## '+name.title(),contents[name]])
            design=root/'docs/forward-design.md';design.write_text('\n\n'.join(parts)+'\n')
            evidence.add(root,'forward-feature','DESIGN','artifact','docs/forward-design.md','A1','Execute the known-answer note behavior fixture','Fixture design before code')
            task=p.load(tp);de=task['evidence']['DESIGN']
            audit={'version':1,'kind':'reasons-alignment','design':{'path':de['path'],'sha256':de['sha256']},'task_contract':evidence.contract(task),
                   'operations':['O1'],'coverage':{c['id']:['O1'] for c in task['acceptance']},'basis':['REQUEST'],
                   'evidence_bindings':{'REQUEST':p.signature(task['evidence']['REQUEST'])},
                   'reviewer':{'name':'Authored fixture reviewer','type':'agent','independent':False},'decision':'ready',
                   'reason':'Known-answer fixture intent and error boundaries were checked before generating its code.','completed_dependencies':{}}
            p.atomic(root/'.runtime/alignment.json',audit)
            evidence.add(root,'forward-feature','ALIGN','artifact','.runtime/alignment.json','A1','Execute the known-answer note behavior fixture','Authored fixture alignment, no human-authorship claim')
            task=p.load(tp);reasons.ready(root,task,tp,'DESIGN','ALIGN')
            result=flow.start(root,'feature','forward-feature','python-backend:implement',inputs={'design':'DESIGN','alignment':'ALIGN'})
            flow.act(root,'feature','step',step='scope',evidence_ids=['DESIGN'])
            selected=flow.selected_context(root,'feature',read_contents=True)
            self.assertTrue(any(d.get('content_scope')=='reasons_selected_operations' for d in selected['documents']))
            # Work is performed only after the bound design is ready and read.
            (root/'backend').mkdir();(root/'tests').mkdir()
            (root/'backend/note.py').write_text('def edit_note(note, actor, text):\n    if note is None:\n        raise LookupError("missing")\n    if note["owner"] != actor:\n        raise PermissionError("not owner")\n    return {**note, "text": text}\n')
            (root/'tests/test_note.py').write_text('import unittest\nfrom backend.note import edit_note\nclass Notes(unittest.TestCase):\n def test_owner(self):\n  original={"owner":"a","text":"before"}\n  self.assertEqual(edit_note(original,"a","after")["text"],"after")\n  self.assertEqual(original["text"],"before")\n def test_non_owner(self):\n  original={"owner":"a","text":"before"}\n  with self.assertRaises(PermissionError): edit_note(original,"b","after")\n  self.assertEqual(original["text"],"before")\n def test_missing(self):\n  with self.assertRaises(LookupError): edit_note(None,"a","after")\n')
            (root/'docs/forward-feature.md').write_text('# Fixture note behavior\nOwners may edit. Non-owners are rejected without mutation. Missing notes are distinguished.\n')
            (root/'docs/index.md').write_text('# Fixture index\n[Note fixture](forward-feature.md) · [Current design](forward-design.md)\n')
            report=checks.run(root,['backend/note.py','tests/test_note.py']);self.assertEqual(report['status'],'passed')
            self.assertEqual(report['results'][0]['test_count'],3);self.assertEqual(report['results'][0]['failed_count'],0)
            evidence.add(root,'forward-feature','CHECK','check',Path(report['report']).relative_to(root).as_posix(),'A1','Execute the known-answer note behavior fixture','Actual three-test note fixture check',check='python')
            p.atomic(root/'.runtime/observed.json',{'behavior_tests':3,'failed':0,'docs':['docs/forward-feature.md','docs/index.md'],'qualification':'Synthetic authored fixture; not model-quality or real product evidence.'})
            evidence.add(root,'forward-feature','OBSERVED','artifact','.runtime/observed.json','A1','Execute the known-answer note behavior fixture','Observed fixture results and document links')
            def act(action,**kwargs):
                result=flow.act(root,'feature',action,**kwargs);self.assertFalse(result['stale']);return result
            for step in ['execute','inspect']:act('step',step=step,evidence_ids=['CHECK'])
            act('move',edge_id='verify-python-backend-implement')
            for step in ['scope','execute','inspect']:act('step',step=step,evidence_ids=['CHECK'])
            act('validate',result='passed',evidence_ids=['CHECK'],reason='Actual fixture owner/non-owner/missing checks passed with scoped current intent')
            self.assertEqual(act('finish')['node'],'python-backend:implement')
            act('validate',result='passed',evidence_ids=['CHECK'],reason='Actual expected fixture behavior matches the bound design')
            act('move',edge_id='document-python-backend-implement')
            for step in ['scope','execute','inspect']:act('step',step=step,evidence_ids=['OBSERVED'])
            act('move',edge_id='verify-docs-maintenance-sync')
            for step in ['scope','execute','inspect']:act('step',step=step,evidence_ids=['OBSERVED'])
            act('validate',result='passed',evidence_ids=['OBSERVED'],reason='Existing fixture behavior/design/index were read and their boundaries match')
            act('finish');act('validate',result='passed',evidence_ids=['OBSERVED'],reason='No intent change or separate reusable wiki fact is needed for this fixture')
            act('move',edge_id='index-sync')
            for step in ['scope','execute','inspect']:act('step',step=step,evidence_ids=['OBSERVED'])
            act('validate',result='passed',evidence_ids=['OBSERVED'],reason='Fixture index selects the current design and behavior document')
            result=act('finish');self.assertEqual(result['flow_status'],'finished');self.assertFalse(result['stack'])
            self.assertNotEqual(p.load(tp)['status'],'complete')
