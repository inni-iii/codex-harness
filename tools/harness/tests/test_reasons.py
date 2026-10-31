"""Design/alignment readiness at every real flow entry, with scoped reuse."""
from pathlib import Path
from contextlib import redirect_stdout
import copy
import io
import json
import unittest

from _support import SOURCE
import test_skill_flows as fixtures
from harness import cli, context, evidence, flow_catalog, provenance as p, reasons, skill_flows as flow


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.FlowTests(methodName='runTest'); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.root = self.f.root
        self.meta = {'version': 1, 'kind': 'reasons-design', 'profile': 'behavioral', 'requirements': ['R1'],
                     'operations': [{'id': 'O1', 'requirements': ['R1'], 'paths': ['example.py'], 'depends_on': [], 'verification': 'Observe accepted result and related errors'},
                                    {'id': 'O2', 'requirements': ['R1'], 'paths': ['other.py'], 'depends_on': [], 'verification': 'Observe independent later result'}],
                     'decisions': [], 'references': []}
        self.design_path = self.root / '.runtime/design.md'
        self.write_design()
        evidence.add(self.root, 'demo', 'DESIGN', 'artifact', '.runtime/design.md', 'A1', 'Observe actual fixture result', 'Known-answer design fixture')
        self.audit = self.review()
        self.write_review()
        self.gate('work', 'main')

    def task(self): return p.load(self.root / 'docs/tasks/demo/task.json')

    def entry(self): return self.task()['evidence']['DESIGN']

    def write_design(self, *, large=False, omit=()):
        parts=['# Fixture design', '```json', json.dumps(self.meta), '```']
        for section in reasons.SECTIONS:
            if section in omit: continue
            parts += ['## ' + section.title()]
            if section == 'operations':
                parts += ['### O1', 'Implement the requested example result; preserve the error boundary.', '### O2', ('UNRELATED_BODY ' * 2000 if large else 'Independent later work.')]
            else: parts += [f'Concrete fixture {section}: use the existing request and preserve its accepted boundary.']
        self.design_path.write_text('\n\n'.join(parts)+'\n')

    def review(self):
        t=self.task(); entry=t['evidence']['DESIGN']
        return {'version':1,'kind':'reasons-alignment','design':{'path':entry['path'],'sha256':entry['sha256']},
                'task_contract':evidence.contract(t),'operations':['O1'],'coverage':{'A1':['O1']},'basis':['E'],
                'evidence_bindings':{'E':p.signature(t['evidence']['E'])},
                'reviewer':{'name':'Fixture reviewer','type':'agent','independent':False},'decision':'ready',
                'reason':'Known-answer fixture scope/decisions mapped to the request; no human approval claim.','completed_dependencies':{}}

    def rehash(self, ident):
        tp=self.root/'docs/tasks/demo/task.json';t=p.load(tp);entry=t['evidence'][ident];entry['sha256']=p.sha(self.root/entry['path']);p.atomic(tp,t)

    def write_review(self):
        p.atomic(self.root/'.runtime/alignment.json',self.audit)
        if 'ALIGN' not in self.task()['evidence']:
            evidence.add(self.root,'demo','ALIGN','artifact','.runtime/alignment.json','A1','Observe actual fixture result','Known-answer current alignment fixture')
        else:self.rehash('ALIGN')

    def update_design(self):
        self.write_design();self.rehash('DESIGN')

    def gate(self, skill, name, *, entry=('alignment',), result=()):
        routes=self.f.routes[skill]
        for route in routes:
            if route['name'] == name:
                route['inputs']=['request','design','alignment'] if 'alignment' in entry else ['request','design'] if 'design' in entry or 'alignment' in result else ['request']
                route['entry_checks']=list(entry);route['result_checks']=list(result)
        fixtures.dump_routes(self.root/f'.agents/skills/{skill}/routes.toml',routes)

    def ready(self):
        return reasons.ready(self.root,self.task(),self.root/'docs/tasks/demo/task.json','DESIGN','ALIGN')

    def start(self, **kwargs):
        return flow.start(self.root,'run','demo','work:main',inputs=kwargs.pop('inputs',{'design':'DESIGN','alignment':'ALIGN'}),**kwargs)

    def test_current_design_and_existing_decision_basis_start_without_question(self):
        self.assertEqual(self.ready()['operations'],['O1'])
        result=self.start();self.assertEqual(result['flow_status'],'running');self.assertIsNone(result['pending'])
        self.f.act('step',step='prepare',evidence_ids=['E'])

    def test_start_rejects_missing_or_unrelated_named_artifact(self):
        for inputs in [{},{'design':'E','alignment':'ALIGN'},{'design':'DESIGN','alignment':'E'}]:
            with self.subTest(inputs=inputs),self.assertRaises(ValueError):self.start(inputs=inputs)
        self.assertFalse(flow.path(self.root,'run').exists())

    def test_transition_and_call_apply_target_gate_and_preserve_rejected_state(self):
        # Begin at an ungated caller, then try the configured target via each edge mode.
        self.f.routes['docs'][0]['finish']=True
        self.f.edges += [{'id':'enter-call','from':'docs:index','to':'work:main','mode':'call','when':'reason','guards':[]},
                         {'id':'enter-transition','from':'docs:index','to':'work:main','mode':'transition','when':'reason','guards':['validated']}]
        self.f.write_graph();flow.start(self.root,'run','demo','docs:index');self.f.steps();self.f.validate()
        before=self.f.state_bytes()
        for edge in ['enter-call','enter-transition']:
            with self.subTest(edge=edge),self.assertRaises(ValueError):self.f.act('move',edge_id=edge,reason='No prepared input')
            self.assertEqual(self.f.state_bytes(),before)
        result=self.f.act('move',edge_id='enter-call',reason='Current design reviewed',inputs={'design':'DESIGN','alignment':'ALIGN'})
        self.assertEqual(result['node'],'work:main')

    def test_restart_cannot_bypass_gate(self):
        self.start();self.f.act('block',reason='Waiting for changed scope')
        (self.root/'example.py').write_text('changed = 1\n');before=self.f.state_bytes()
        with self.assertRaises(ValueError):self.f.act('restart',reason='New source but no readiness inputs')
        self.assertEqual(self.f.state_bytes(),before)
        self.assertEqual(self.f.act('restart',reason='New source',inputs={'design':'DESIGN','alignment':'ALIGN'})['flow_status'],'running')

    def test_stale_design_hash_and_retargeted_entry_are_not_accepted(self):
        self.design_path.write_text(self.design_path.read_text()+'\nChanged decision\n')
        with self.assertRaises(ValueError):self.ready()
        self.rehash('DESIGN')
        with self.assertRaises(ValueError):self.ready()

    def test_stale_task_contract_and_missing_coverage_are_rejected(self):
        tp=self.root/'docs/tasks/demo/task.json';t=p.load(tp);t['goal']='Different outcome';p.atomic(tp,t)
        with self.assertRaises(ValueError):self.ready()
        self.audit=self.review();self.audit['coverage']={};self.write_review()
        with self.assertRaises(ValueError):self.ready()

    def test_unknown_or_uncovered_selected_operation_is_rejected(self):
        self.audit['operations']=['MISSING'];self.write_review()
        with self.assertRaises(ValueError):self.ready()
        self.audit=self.review();self.audit['operations']=['O1','O2'];self.write_review()
        with self.assertRaises(ValueError):self.ready()

    def test_task_scope_cannot_extend_beyond_selected_operations(self):
        tp=self.root/'docs/tasks/demo/task.json';t=p.load(tp);t['scope']=['outside.py'];p.atomic(tp,t)
        self.audit=self.review();self.write_review()
        with self.assertRaises(ValueError):self.ready()

    def test_wildcard_task_scope_does_not_broaden_concrete_authority(self):
        tp=self.root/'docs/tasks/demo/task.json';t=p.load(tp);t['scope']=['*.py'];p.atomic(tp,t)
        self.audit=self.review();self.write_review()
        with self.assertRaises(ValueError):self.ready()

    def test_unrelated_open_decision_does_not_block_independent_operation(self):
        self.meta['decisions']=[{'id':'D1','status':'open','operations':['O2'],'reason':'User choice for the independent later operation'}]
        self.update_design();self.audit=self.review();self.write_review()
        self.assertEqual(self.ready()['operations'],['O1'])
        self.meta['decisions'][0]['operations']=['O1'];self.update_design();self.audit=self.review();self.write_review()
        with self.assertRaises(ValueError):self.ready()

    def test_missing_dependencies_block_until_real_evidence_is_connected(self):
        self.meta['operations'][0]['depends_on']=['O2'];self.update_design();self.audit=self.review();self.write_review()
        with self.assertRaises(ValueError):self.ready()
        self.audit['completed_dependencies']={'O2':'E'};self.write_review()
        self.assertEqual(self.ready()['operations'],['O1'])

    def test_selected_dependencies_must_be_in_executable_order(self):
        self.meta['operations'][1]['depends_on']=['O1'];self.update_design();self.audit=self.review()
        self.audit['operations']=['O2','O1'];self.audit['coverage']={'A1':['O1','O2']};self.write_review()
        with self.assertRaises(ValueError):self.ready()

    def test_cycles_unknown_requirement_and_duplicate_ids_are_rejected(self):
        original=copy.deepcopy(self.meta)
        variants=[]
        v=copy.deepcopy(original);v['operations'][0]['depends_on']=['O2'];v['operations'][1]['depends_on']=['O1'];variants.append(v)
        v=copy.deepcopy(original);v['operations'][0]['requirements']=['R2'];variants.append(v)
        v=copy.deepcopy(original);v['operations'][1]['id']='O1';variants.append(v)
        for meta in variants:
            with self.subTest(meta=meta):
                self.meta=meta;self.update_design()
                with self.assertRaises(ValueError):reasons.document(self.root,self.entry())

    def test_fenced_fake_operations_do_not_satisfy_a_declared_step(self):
        content=self.design_path.read_text().replace('### O1\n\nImplement','```text\n### O1\n```\n\nImplement')
        self.design_path.write_text(content);self.rehash('DESIGN')
        with self.assertRaises(ValueError):reasons.document(self.root,self.entry())

    def test_editorial_change_can_use_reasoned_small_contract(self):
        self.meta['profile']='editorial';self.meta['not_applicable']={name:'Existing public behavior is unchanged; this edit only corrects a label.' for name in ['entities','approach','structure','norms']}
        self.write_design(omit=self.meta['not_applicable']);self.rehash('DESIGN');self.audit=self.review();self.write_review()
        self.assertEqual(self.ready()['design']['profile'],'editorial')
        self.meta['profile']='behavioral';self.update_design()
        with self.assertRaises(ValueError):reasons.document(self.root,self.entry())

    def test_referenced_contract_changes_invalidate_current_readiness(self):
        ref=self.root/'contract.md';ref.write_text('Existing agreed boundary')
        self.meta['references']=[{'path':'contract.md','sha256':p.sha(ref)}];self.update_design();self.audit=self.review();self.write_review();self.start()
        ref.write_text('Changed agreed boundary')
        self.assertTrue(flow.inspect(self.root,'run')['stale'])
        with self.assertRaises(ValueError):self.f.act('step',step='prepare',evidence_ids=['E'])

    def test_current_bound_design_is_rechecked_on_resume(self):
        self.start();self.design_path.write_text(self.design_path.read_text()+'\nNew text\n')
        self.assertTrue(flow.inspect(self.root,'run')['stale'])
        with self.assertRaises(ValueError):self.f.act('step',step='prepare',evidence_ids=['E'])

    def test_call_inherits_current_readiness_and_returns_to_next_step(self):
        self.gate('work','next');self.start();self.f.act('step',step='prepare',evidence_ids=['E'])
        result=self.f.act('move',edge_id='side',reason='Need scoped helper')
        self.assertEqual(result['node'],'work:next');self.f.steps();self.f.validate();result=self.f.act('finish')
        self.assertEqual(result['completed_steps'],['prepare']);self.assertFalse(result['stale'])

    def test_selected_context_omits_unrelated_operation_body(self):
        self.write_design(large=True);self.rehash('DESIGN');self.audit=self.review();self.write_review();self.start()
        result=flow.selected_context(self.root,'run',read_contents=True)
        body=next(d for d in result['documents'] if d['path']=='.runtime/design.md')
        self.assertEqual(body['selected_operations'],['O1']);self.assertIn('## Safeguards',body['content']);self.assertNotIn('UNRELATED_BODY',body['content'])

    def test_operation_selection_preserves_fenced_examples_of_selected_work(self):
        content=self.design_path.read_text().replace('### O1\n\nImplement', '### O1\n\n```text\n### O2\nREQUIRED_O1_EXAMPLE\n```\n\nImplement')
        self.design_path.write_text(content);self.rehash('DESIGN');self.audit=self.review();self.write_review();self.start()
        result=flow.selected_context(self.root,'run',read_contents=True)
        body=next(d for d in result['documents'] if d['path']=='.runtime/design.md')
        self.assertIn('REQUIRED_O1_EXAMPLE',body['content'])
        self.assertNotIn('Independent later work.',body['content'])

    def test_alignment_template_starts_pending_and_existing_file_is_preserved(self):
        result=reasons.alignment_template(self.root,self.task(),self.root/'docs/tasks/demo/task.json','DESIGN',['O1'],'.runtime/new-review.json')
        template=p.load(self.root/result['path']);self.assertEqual(template['decision'],'pending');self.assertFalse(template['basis'])
        with self.assertRaises(ValueError):reasons.alignment_template(self.root,self.task(),self.root/'docs/tasks/demo/task.json','DESIGN',['O1'],'.runtime/new-review.json')

    def test_basis_cannot_be_missing_or_the_design_itself(self):
        for basis in [[],['MISSING'],['DESIGN']]:
            with self.subTest(basis=basis):
                self.audit['basis']=basis;self.write_review()
                with self.assertRaises(ValueError):self.ready()

    def test_plan_result_checks_reject_label_only_passes(self):
        self.gate('docs','index',entry=(),result=('design',))
        flow.start(self.root,'run','demo','docs:index');self.f.steps()
        with self.assertRaises(ValueError):self.f.validate()
        self.f.validate(ids=['DESIGN'])

    def test_alignment_result_check_binds_review_to_the_input_design(self):
        self.gate('docs','index',entry=('design',),result=('alignment',))
        flow.start(self.root,'run','demo','docs:index',inputs={'design':'DESIGN'});self.f.steps()
        with self.assertRaises(ValueError):self.f.validate()
        self.f.validate(ids=['ALIGN'])

    def test_cli_ready_and_template_are_reviewable_without_starting_a_flow(self):
        out=io.StringIO()
        with redirect_stdout(out):code=cli.main(['flow','ready','--task','demo','--design','DESIGN','--alignment','ALIGN'],root=self.root)
        self.assertEqual(code,0);self.assertEqual(json.loads(out.getvalue())['operations'],['O1'])

    def test_catalog_rejects_unknown_checks_or_missing_typed_inputs(self):
        records=copy.deepcopy(self.f.routes['work'])
        for mutate in ['unknown','missing']:
            changed=copy.deepcopy(records)
            if mutate=='unknown':changed[0]['entry_checks']=['shell-command']
            else:changed[0]['inputs']=['request']
            fixtures.dump_routes(self.root/'.agents/skills/work/routes.toml',changed)
            with self.assertRaises(ValueError):flow_catalog.load(self.root)


class RepositoryReadinessTests(unittest.TestCase):
    def test_real_implementation_routes_require_design_and_alignment(self):
        catalog=flow_catalog.load(SOURCE)
        for node in ['python-backend:implement','svelte-frontend:implement','postgres:change','maintain-skills:maintain','verify-work:repair','verify-work:check']:
            with self.subTest(node=node):
                r=catalog['nodes'][node];self.assertIn('alignment',r['entry_checks']);self.assertTrue({'design','alignment'}<=set(r['inputs']))
        self.assertEqual({r['skill'] for r in catalog['nodes'].values()}, {p.name for p in (SOURCE/'.agents/skills').iterdir() if p.is_dir()})

    def test_reasons_and_spec_topics_select_only_owned_procedures(self):
        for topic, expected in [('reasons','plan-project/references/reasons-canvas.md'),('spec-maintenance','docs-maintenance/references/specifications.md')]:
            result=context.select(SOURCE,'research',[],[topic],read=True)
            self.assertIn('.agents/skills/'+expected,{d['path'] for d in result['documents']})
