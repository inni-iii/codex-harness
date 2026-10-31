"""Real persistent route transitions, evidence, waiting and recovery boundaries."""
from pathlib import Path
from contextlib import redirect_stdout
import copy
import io
import json
import shutil
import sys
import tempfile
import unittest

from _support import SOURCE
from harness import checks, cli, evidence, flow_catalog as catalog, provenance as p, skill_flows as flow, skills, tasks


def route(name, *, finish=True, calls=(), types=('artifact',), inputs=('request',)):
    return {'name': name, 'when': 'A scoped fixture request', 'kind': 'implement',
            'inputs': list(inputs), 'documents': [],
            'steps': [{'id': 'prepare', 'instruction': 'Inspect the fixture input'},
                      {'id': 'perform', 'instruction': 'Perform the requested fixture change'}],
            'validation': 'Compare actual fixture output and its boundaries',
            'evidence_types': list(types), 'required_calls': list(calls), 'finish': finish}


def dump_routes(path, routes):
    lines = ['version=1']
    for record in routes:
        lines.append('[[routes]]')
        for key, value in record.items():
            if key != 'steps':
                lines.append(key + '=' + (str(value).lower() if isinstance(value, bool) else json.dumps(value)))
        for step in record['steps']:
            lines += ['[[routes.steps]]', 'id=' + json.dumps(step['id']), 'instruction=' + json.dumps(step['instruction'])]
    path.write_text('\n'.join(lines) + '\n')


class FlowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='skill-flow-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.routes = {'work': [route('main', finish=False, calls=['verify:check']), route('next')],
                       'verify': [route('check')], 'docs': [route('index')]}
        for skill, records in self.routes.items():
            folder = self.root / f'.agents/skills/{skill}'
            folder.mkdir(parents=True)
            (folder / 'SKILL.md').write_text(f'---\nname: {skill}\ndescription: A fixture\n---\nRead the fixture request.\n')
            dump_routes(folder / 'routes.toml', records)
        (self.root / '.agents/context.toml').write_text('version=1\n' + '\n'.join(
            f'[[skills]]\nname="{skill}"\nwhen="Fixture"\ntopics=["{skill}"]\n' for skill in self.routes))
        self.edges = [
            {'id': 'verify', 'from': 'work:main', 'to': 'verify:check', 'mode': 'call', 'when': 'steps_complete', 'guards': []},
            {'id': 'done', 'from': 'work:main', 'to': 'docs:index', 'mode': 'transition', 'when': 'steps_complete', 'guards': ['validated']},
            {'id': 'retry', 'from': 'work:main', 'to': 'work:main', 'mode': 'transition', 'when': 'reason', 'guards': ['failed']},
            {'id': 'side', 'from': 'work:main', 'to': 'work:next', 'mode': 'call', 'when': 'reason', 'guards': []},
            {'id': 'callee-next', 'from': 'verify:check', 'to': 'work:next', 'mode': 'transition', 'when': 'steps_complete', 'guards': ['validated']},
            {'id': 'next-check', 'from': 'work:next', 'to': 'verify:check', 'mode': 'call', 'when': 'reason', 'guards': []},
            {'id': 'choose-docs', 'from': 'work:main', 'to': 'docs:index', 'mode': 'transition', 'when': 'user_choice', 'guards': ['validated'], 'choice': 'docs'},
            {'id': 'choose-next', 'from': 'work:main', 'to': 'work:next', 'mode': 'transition', 'when': 'user_choice', 'guards': ['validated'], 'choice': 'next'}]
        self.write_graph()
        config = self.root / 'tools/harness/harness.toml'; config.parent.mkdir(parents=True)
        config.write_text('version=1\n[[checks]]\nid="python"\ncommand=["{python}","-m","unittest","discover","-s","tests","-v"]\npaths=["**"]\ntest_summary="unittest"\ntimeout=30\n')
        (self.root / 'AGENTS.md').write_text('Fixture common rules')
        (self.root / 'docs').mkdir(exist_ok=True)
        (self.root / 'docs/index.md').write_text('Fixture index')
        tasks.create(self.root, 'demo', 'implement', 'Fixture change', ['Fixture observable output'])
        task = self.root / 'docs/tasks/demo/task.json'
        data = p.load(task); data['scope'] = ['example.py']; data['acceptance'][0]['method'] = 'Observe actual fixture result'; p.atomic(task, data)
        proof = self.root / '.runtime/output.md'; proof.parent.mkdir(parents=True, exist_ok=True); proof.write_text('Observed fixture output')
        evidence.add(self.root, 'demo', 'E', 'artifact', '.runtime/output.md', 'A1', 'Observe actual fixture result', 'Fixture observation')

    def write_graph(self):
        lines = ['version=1']
        for edge in self.edges:
            lines += ['[[edges]]'] + [key + '=' + json.dumps(value) for key, value in edge.items()]
        (self.root / catalog.CATALOG).write_text('\n'.join(lines) + '\n')

    def start(self, **kwargs):
        return flow.start(self.root, 'run', 'demo', 'work:main', **kwargs)

    def act(self, action, **kwargs):
        return flow.act(self.root, 'run', action, **kwargs)

    def steps(self, ids=('E',)):
        self.act('step', step='prepare', evidence_ids=list(ids))
        return self.act('step', step='perform', evidence_ids=list(ids))

    def validate(self, result='passed', ids=('E',)):
        return self.act('validate', result=result, evidence_ids=list(ids), reason='Compared fixture output and boundaries')

    def verified_parent(self):
        self.steps(); self.act('move', edge_id='verify')
        self.steps(); self.validate(); self.act('finish')
        return self.validate()

    def state_bytes(self):
        return flow.path(self.root, 'run').read_bytes()

    def test_full_call_return_transition_and_root_finish_leave_task_open(self):
        self.start(); self.verified_parent()
        result = self.act('move', edge_id='done')
        self.assertEqual(result['node'], 'docs:index')
        self.steps(); self.validate(); result = self.act('finish')
        self.assertEqual(result['flow_status'], 'finished')
        self.assertNotEqual(p.load(self.root / 'docs/tasks/demo/task.json')['status'], 'complete')
        with self.assertRaises(ValueError): self.act('step', step='prepare', evidence_ids=['E'])

    def test_return_resumes_next_unfinished_step_instead_of_restarting(self):
        self.start(); self.act('step', step='prepare', evidence_ids=['E'])
        self.act('move', edge_id='side', reason='Need supporting work')
        self.steps(); self.validate(); result = self.act('finish')
        self.assertEqual(result['completed_steps'], ['prepare'])
        self.assertEqual(result['phase'], 'steps')
        self.act('step', step='perform', evidence_ids=['E'])

    def test_callee_transition_preserves_original_call_return(self):
        self.start(); self.steps(); self.act('move', edge_id='verify')
        self.steps(); self.validate(); self.act('move', edge_id='callee-next')
        self.steps(); self.validate(); result = self.act('finish')
        self.assertEqual(result['node'], 'work:main')
        self.assertEqual(result['last_return']['requested_node'], 'verify:check')
        self.assertEqual(result['last_return']['finished_node'], 'work:next')
        self.validate()

    def test_failed_child_cannot_satisfy_required_call_and_repair_reenters(self):
        self.start(); self.steps(); self.act('move', edge_id='verify')
        self.validate('failed'); result = self.act('finish')
        self.assertEqual(result['last_return']['result'], 'failed')
        with self.assertRaises(ValueError): self.validate()
        result = self.act('move', edge_id='retry', reason='Repair observed failure')
        self.assertEqual(result['completed_steps'], [])
        self.assertIsNone(result['validation'])

    def test_steps_complete_is_distinct_from_validation_and_cannot_skip_required_call(self):
        self.start(); before = self.state_bytes()
        with self.assertRaises(ValueError): self.act('move', edge_id='verify')
        with self.assertRaises(ValueError): self.validate()
        self.assertEqual(self.state_bytes(), before)
        self.steps()
        with self.assertRaises(ValueError): self.act('move', edge_id='done')
        with self.assertRaises(ValueError): self.validate()
        with self.assertRaises(ValueError): self.act('finish')

    def test_step_order_duplicate_and_missing_evidence_are_rejected(self):
        self.start()
        for kwargs in [{'step': 'perform', 'evidence_ids': ['E']}, {'step': 'prepare'}, {'step': 'prepare', 'evidence_ids': ['missing']}]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError): self.act('step', **kwargs)
        self.act('step', step='prepare', evidence_ids=['E'])
        with self.assertRaises(ValueError): self.act('step', step='prepare', evidence_ids=['E'])

    def test_reason_cannot_invent_an_edge_or_bypass_success_guard(self):
        self.start()
        with self.assertRaises(ValueError): self.act('move', edge_id='not-registered', reason='Please allow it')
        with self.assertRaises(ValueError): self.act('move', edge_id='done', reason='Skip verification')
        with self.assertRaises(ValueError): self.act('move', edge_id='side')
        with self.assertRaises(ValueError): self.act('move', edge_id='retry', reason='No failure was observed')

    def test_user_wait_blocks_advancement_and_answer_is_question_bound(self):
        self.start(); self.verified_parent()
        asked = self.act('ask', question='Choose the next fixture flow')
        qid = asked['pending']['id']
        for action, args in [('finish', {}), ('move', {'edge_id': 'done'}), ('step', {'step': 'prepare', 'evidence_ids': ['E']})]:
            with self.subTest(action=action), self.assertRaises(ValueError): self.act(action, **args)
        for q, c in [('old-question', 'docs'), (qid, 'unknown')]:
            with self.assertRaises(ValueError): self.act('answer', question_id=q, choice=c, evidence_ids=['E'], reason='Observed actual user answer')
        self.act('answer', question_id=qid, choice='docs', evidence_ids=['E'], reason='Observed actual user answer')
        with self.assertRaises(ValueError): self.act('move', edge_id='choose-next')
        result = self.act('move', edge_id='choose-docs')
        self.assertEqual(result['node'], 'docs:index')
        with self.assertRaises(ValueError): self.act('answer', question_id=qid, choice='docs', evidence_ids=['E'], reason='Replay')

    def test_source_edit_invalidates_success_and_allows_registered_reentry(self):
        self.start(); self.verified_parent()
        (self.root / 'example.py').write_text('value = 2\n')
        self.assertTrue(flow.inspect(self.root, 'run')['stale'])
        with self.assertRaises(ValueError): self.act('move', edge_id='done')
        result = self.act('move', edge_id='retry', reason='Changed result needs verification')
        self.assertEqual(result['phase'], 'steps')

    def test_changed_evidence_is_rejected_without_overwriting_flow(self):
        self.start(); self.act('step', step='prepare', evidence_ids=['E']); before = self.state_bytes()
        (self.root / '.runtime/output.md').write_text('Different bytes')
        self.assertTrue(flow.inspect(self.root, 'run')['stale'])
        with self.assertRaises(ValueError): self.act('step', step='perform', evidence_ids=['E'])
        self.assertEqual(self.state_bytes(), before)

    def test_changed_task_contract_requires_explicit_restart_and_preserves_history(self):
        self.start(); self.steps()
        tp = self.root / 'docs/tasks/demo/task.json'; task = p.load(tp); task['goal'] = 'Changed request'; p.atomic(tp, task)
        with self.assertRaises(ValueError): self.act('move', edge_id='verify')
        result = self.act('restart', reason='Resume the changed request')
        self.assertEqual(result['completed_steps'], [])
        self.assertGreater(result['revision'], 3)

    def test_catalog_change_requires_restart(self):
        self.start(); self.edges[0]['id'] = 'verify-new'; self.write_graph()
        with self.assertRaises(ValueError): self.act('step', step='prepare', evidence_ids=['E'])
        self.assertTrue(flow.inspect(self.root, 'run')['stale'])
        self.act('restart', reason='Use updated route contract')

    def test_no_progress_reentry_blocks_and_empty_restart_does_not_reset_limit(self):
        self.start(max_visits=2)
        self.validate('failed'); self.act('move', edge_id='retry', reason='First retry')
        self.validate('failed'); result = self.act('move', edge_id='retry', reason='Same retry')
        self.assertEqual(result['flow_status'], 'blocked')
        with self.assertRaises(ValueError): self.act('restart', reason='Repeat without progress')
        (self.root / 'example.py').write_text('new_result = True\n')
        self.assertEqual(self.act('restart', reason='New source result')['flow_status'], 'running')

    def test_movement_budget_is_not_reset_by_new_content(self):
        self.start(max_moves=1); self.steps(); self.act('move', edge_id='verify')
        self.steps(); self.validate(); self.assertEqual(self.act('finish')['flow_status'], 'blocked')
        (self.root / 'example.py').write_text('new = 1\n')
        self.assertEqual(self.act('restart', reason='New source')['flow_status'], 'blocked')

    def test_recursive_calls_and_depth_limit_are_rejected(self):
        self.start(); self.steps(); self.act('move', edge_id='verify'); self.steps(); self.validate()
        self.act('move', edge_id='callee-next')
        with self.assertRaises(ValueError): self.act('move', edge_id='next-check', reason='Would recurse to active call target')

    def test_lock_revision_and_integrity_rejections_preserve_saved_state(self):
        self.start(); before = self.state_bytes()
        lock = flow.path(self.root, 'run').with_suffix('.lock'); lock.write_text('Active writer')
        with self.assertRaises(ValueError): self.act('block', reason='Blocked')
        self.assertEqual(self.state_bytes(), before); lock.unlink()
        with self.assertRaises(ValueError): self.act('block', reason='Blocked', expect_revision=0)
        data = json.loads(before); data['status'] = 'finished'; flow.path(self.root, 'run').write_text(json.dumps(data))
        with self.assertRaises(ValueError): flow.inspect(self.root, 'run')

    def test_runtime_path_escape_and_symlink_are_rejected(self):
        with self.assertRaises(ValueError): flow.start(self.root, '../outside', 'demo', 'work:main')
        with tempfile.TemporaryDirectory() as outside:
            link = self.root / '.runtime/skill-flows'; link.symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError): self.start()

    def test_required_inputs_bind_existing_evidence_and_request_cannot_be_overridden(self):
        records = self.routes['work']; records[1]['inputs'].append('design')
        dump_routes(self.root / '.agents/skills/work/routes.toml', records)
        self.start()
        for inputs in [{}, {'unknown': 'E'}, {'request': 'E'}, {'design': 'missing'}]:
            with self.subTest(inputs=inputs), self.assertRaises(ValueError): self.act('move', edge_id='side', reason='Needs input', inputs=inputs)
        result = self.act('move', edge_id='side', reason='Has design', inputs={'design': 'E'})
        self.assertEqual(result['node'], 'work:next')

    def test_terminal_route_cannot_bypass_required_success_continuation(self):
        self.start(); self.verified_parent()
        with self.assertRaises(ValueError): self.act('finish')

    def test_current_context_keeps_indexes_and_omits_target_procedure(self):
        self.start(); result = flow.selected_context(self.root, 'run', read_contents=True)
        selected = {d['path'] for d in result['documents']}
        self.assertIn('docs/index.md', selected); self.assertIn('AGENTS.md', selected)
        self.assertIn('.agents/skills/work/SKILL.md', selected)
        self.assertNotIn('.agents/skills/verify/SKILL.md', selected)
        self.assertTrue(all(d.get('content') for d in result['documents']))
        self.assertTrue(any(e['to'] == 'verify:check' for e in result['outgoing']))

    def test_real_behavior_check_evidence_is_required_and_stale_checks_cannot_pass(self):
        self.routes['verify'][0]['evidence_types'] = ['check']
        dump_routes(self.root / '.agents/skills/verify/routes.toml', self.routes['verify'])
        tests = self.root / 'tests'; tests.mkdir()
        (tests / 'test_output.py').write_text('import unittest\nclass Output(unittest.TestCase):\n def test_result(self): self.assertEqual(2 + 2, 4)\n')
        report = checks.run(self.root, ['tests/test_output.py'])
        self.assertEqual(report['status'], 'passed')
        evidence.add(self.root, 'demo', 'CHECK', 'check', Path(report['report']).relative_to(self.root).as_posix(), 'A1', 'Observe actual fixture result', 'Actual one-test runner result', check='python')
        self.start(); self.steps(); self.act('move', edge_id='verify'); self.steps()
        with self.assertRaises(ValueError): self.validate()
        self.validate(ids=['CHECK']); self.act('finish')
        (self.root / 'example.py').write_text('changed = True\n')
        with self.assertRaises(ValueError): self.validate()

    def test_failed_callee_transition_cannot_return_a_success_from_unrelated_plan(self):
        self.edges.append({'id': 'recover-plan', 'from': 'verify:check', 'to': 'work:next', 'mode': 'transition', 'when': 'reason', 'guards': ['failed']})
        self.write_graph()
        self.start(); self.steps(); self.act('move', edge_id='verify')
        self.validate('failed'); self.act('move', edge_id='recover-plan', reason='Need a new plan')
        self.steps(); self.validate(); result = self.act('finish')
        self.assertEqual(result['last_return']['result'], 'failed')
        with self.assertRaises(ValueError): self.validate()

    def test_named_input_cannot_be_retargeted_by_editing_task_evidence(self):
        self.routes['work'][1]['inputs'].append('design')
        dump_routes(self.root / '.agents/skills/work/routes.toml', self.routes['work'])
        self.start(); self.act('move', edge_id='side', reason='Need design', inputs={'design': 'E'})
        tp = self.root / 'docs/tasks/demo/task.json'; task = p.load(tp)
        (self.root / '.runtime/replacement.md').write_text('A different design')
        task['evidence']['E']['path'] = '.runtime/replacement.md'
        task['evidence']['E']['sha256'] = p.sha(self.root / '.runtime/replacement.md')
        p.atomic(tp, task)
        self.assertTrue(flow.inspect(self.root, 'run')['stale'])
        with self.assertRaises(ValueError): self.act('step', step='prepare', evidence_ids=['E'])

    def test_return_continuation_must_supply_original_requested_evidence_types(self):
        self.routes['verify'][0]['evidence_types'] = ['check']
        dump_routes(self.root / '.agents/skills/verify/routes.toml', self.routes['verify'])
        # It is invalid to turn a failed check into an artifact-only success elsewhere.
        self.edges.append({'id': 'recover-plan', 'from': 'verify:check', 'to': 'work:next', 'mode': 'transition', 'when': 'reason', 'guards': ['failed']})
        self.write_graph(); self.start(); self.steps(); self.act('move', edge_id='verify')
        self.validate('failed'); self.act('move', edge_id='recover-plan', reason='Replan the failed request')
        self.steps(); self.validate(); result = self.act('finish')
        self.assertEqual(result['last_return']['result'], 'failed')

    def test_call_depth_limit_without_a_recursive_target(self):
        self.start(max_depth=1); self.act('move', edge_id='side', reason='Supporting work')
        with self.assertRaises(ValueError): self.act('move', edge_id='next-check', reason='Would exceed depth')

    def test_generated_skill_has_a_valid_route_when_graph_is_active(self):
        skills.create(self.root, 'new-skill', 'Inspect fixture output', 'Inspect the actual fixture output.')
        cat = catalog.load(self.root)
        self.assertIn('new-skill:main', cat['nodes'])
        self.assertTrue(cat['nodes']['new-skill:main']['finish'])

    def test_procedure_body_change_requires_restart(self):
        self.start(); (self.root / '.agents/skills/work/SKILL.md').write_text('A different procedure contract')
        with self.assertRaises(ValueError): self.act('step', step='prepare', evidence_ids=['E'])
        self.act('restart', reason='Read the changed procedure and start again')

    def test_cli_roundtrip_and_invalid_input_binding(self):
        def run(*args):
            out = io.StringIO()
            with redirect_stdout(out): code = cli.main(['flow', *args], root=self.root)
            return code, json.loads(out.getvalue())
        self.assertEqual(run('catalog')[0], 0)
        self.assertEqual(run('start', 'run', '--task', 'demo', '--node', 'work:main')[0], 0)
        code, result = run('context', 'run', '--read'); self.assertEqual(code, 0); self.assertEqual(result['node'], 'work:main')
        self.assertEqual(run('step', 'run', 'prepare', '--evidence', 'E')[0], 0)
        self.assertEqual(run('status', 'run')[1]['completed_steps'], ['prepare'])
        self.assertEqual(run('move', 'run', 'side', '--reason', 'Need subtask', '--input', 'x=E', '--input', 'x=E')[0], 2)

    def test_catalog_rejects_bad_endpoints_conditions_and_unconditional_success(self):
        original = copy.deepcopy(self.edges)
        mutations = [('to', 'unknown:node'), ('when', 'always'), ('mode', 'exec'), ('guards', []), ('guards', ['made-up']), ('command', ['shell'])]
        for key, value in mutations:
            with self.subTest(key=key, value=value):
                self.edges = copy.deepcopy(original); self.edges[1][key] = value; self.write_graph()
                with self.assertRaises(ValueError): catalog.load(self.root)
        self.edges = original; self.write_graph()

    def test_catalog_rejects_missing_required_call_and_orphaned_continuation(self):
        self.edges = [e for e in self.edges if e['id'] != 'verify']; self.write_graph()
        with self.assertRaises(ValueError): catalog.load(self.root)
        self.routes['work'][0]['required_calls'] = []; dump_routes(self.root / '.agents/skills/work/routes.toml', self.routes['work'])
        self.edges = [e for e in self.edges if e['from'] != 'work:main']; self.write_graph()
        with self.assertRaises(ValueError): catalog.load(self.root)


class RepositoryFlowTests(unittest.TestCase):
    def test_real_catalog_covers_all_skills_and_read_only_routes_can_finish(self):
        cat = catalog.load(SOURCE)
        folders = {p.name for p in (SOURCE / '.agents/skills').iterdir() if p.is_dir()}
        self.assertEqual({n['skill'] for n in cat['nodes'].values()}, folders)
        for node in ['docs-maintenance:navigation', 'docs-maintenance:wiki-query', 'docs-maintenance:wiki-lint']:
            self.assertTrue(cat['nodes'][node]['finish'])
        for node in ['python-backend:implement', 'svelte-frontend:implement']:
            self.assertFalse(cat['nodes'][node]['finish'])
            self.assertIn('verify-work:check', cat['nodes'][node]['required_calls'])
