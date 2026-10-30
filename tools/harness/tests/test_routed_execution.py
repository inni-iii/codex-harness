"""Process-level contracts for route → worker and the prompt handoff.

The executable below substitutes for Codex; these are not live model tests.
"""
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import textwrap
import time
import tomllib
import unittest
from unittest.mock import patch

from _support import SOURCE
from harness.routing.cli import parser
from harness.routing.execution import enqueue, digest
from harness.routing.hooks import prompt_hook
from test_routing import catalog_payload


FAKE = r'''
import json, os, pathlib, sys, time, uuid
root = pathlib.Path(__file__).parent
args = sys.argv[1:]
mode = (root / 'mode').read_text() if (root / 'mode').exists() else ''
def emit(value):
    print(json.dumps(value), flush=True)
def option(name):
    return args[args.index(name) + 1]
if args[:2] == ['debug', 'models']:
    if mode == 'catalog_error': sys.exit(3)
    print((root / 'catalog.json').read_text())
    sys.exit(0)
raw = sys.stdin.read()
with (root / 'calls.jsonl').open('a') as trace:
    trace.write(json.dumps({'args': args, 'stdin': raw}) + '\n')
output = pathlib.Path(option('--output-last-message'))
if '--output-schema' in args:
    if mode == 'classifier_error': sys.exit(4)
    classification = {'task_type':'implement','complexity':'medium','ambiguity':'low',
                      'failure_impact':'medium','verifiability':'deterministic',
                      'context_dependency':'none','missing_context':[],
                      'uncertainties':[], 'required_capabilities':['text']}
    if 'complex task' in raw:
        classification.update(complexity='high',ambiguity='high',failure_impact='high')
    if mode == 'mutate_context': (root/'context.txt').write_text('new source bytes')
    output.write_text(json.dumps(classification))
    emit({'type':'turn.completed'})
    sys.exit(0)
if mode == 'timeout': time.sleep(30)
if mode == 'output_limit':
    print('X' * 10000,flush=True)
    time.sleep(30)
if mode == 'malformed':
    print('not json',flush=True)
    time.sleep(30)
if mode == 'deep_json':
    print('[' * 2000 + ']' * 2000,flush=True)
    time.sleep(30)
if mode == 'failure_event':
    emit({'type':'turn.failed','error':{'message':'SYNTHETIC_SECRET'}})
    sys.exit(0)
if mode == 'exit_error':
    print('SYNTHETIC_SECRET',file=sys.stderr)
    sys.exit(7)
identifier = str(uuid.uuid4())
emit({'type':'thread.started','thread_id':identifier})
emit({'type':'turn.started'})
cwd = pathlib.Path(option('-C'))
data = json.loads(raw[raw.index('\n{') + 1:])
readme = cwd/'README.md'
if 'before' in data['user_request'] and readme.exists():
    readme.write_text(readme.read_text().replace('before','after'))
if mode != 'no_observation':
    sessions = pathlib.Path(os.environ['CODEX_HOME'])/'sessions'/'2026'/'10'/'31'
    sessions.mkdir(parents=True,exist_ok=True)
    model = option('--model')
    effort = json.loads(next(x.split('=',1)[1] for x in args if x.startswith('model_reasoning_effort=')))
    if mode == 'mismatch': model = 'unexpected-model'
    record = {'type':'turn_context','payload':{'cwd':str(cwd),'model':model,'effort':effort}}
    (sessions/f'rollout-test-{identifier}.jsonl').write_text(json.dumps(record)+'\n')
if mode == 'fifo_response': os.mkfifo(output)
elif mode != 'missing_response':
    output.write_text('worker response: ' + data['user_request'])
if mode != 'incomplete':
    emit({'type':'turn.completed','usage':{'input_tokens':17,'cached_input_tokens':3,'output_tokens':8}})
'''


class RoutedExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='routing with spaces ')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.project = self.root / 'project'
        self.project.mkdir()
        (self.project / 'README.md').write_text('before\n')
        self.executable = self.root / 'codex-fake'
        self.executable.write_text('#!' + sys.executable + '\n' + textwrap.dedent(FAKE))
        self.executable.chmod(0o700)
        self.catalog = self.root / 'catalog.json'
        self.catalog.write_text(json.dumps(catalog_payload()))
        self.environment = {**os.environ, 'CODEX_HOME': str(self.root / 'codex-home')}
        self.environment.pop('HARNESS_ROUTING_DECISION', None)
        self.env_patch = patch.dict(os.environ, self.environment, clear=True)
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

    def calls(self):
        path = self.root / 'calls.jsonl'
        return [json.loads(x) for x in path.read_text().splitlines()] if path.exists() else []

    def command(self, *args, stdin=None, expected=0, timeout=10):
        result = subprocess.run([sys.executable, str(SOURCE/'tools/harness/run.py'),
                                 'run', '--cwd', str(self.project), '--codex', str(self.executable),
                                 *args], input=stdin, capture_output=True, text=True,
                                env=dict(os.environ), timeout=timeout)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def mode(self, mode):
        (self.root / 'mode').write_text(mode)

    def test_literal_edit_routes_and_changes_file_with_explicit_pair_and_stdin(self):
        prompt = "문구만 'before'를 'after'로 바꿔줘"
        result = self.command('--sandbox','workspace-write', '-', stdin=prompt)
        self.assertEqual((self.project/'README.md').read_text(), 'after\n')
        self.assertEqual(result['selected'], {'model':'gpt-6-luna','effort':'low'})
        self.assertEqual(result['observation_status'], 'verified_configuration')
        self.assertEqual(result['quality'], 'unrated')
        self.assertEqual(result['usage']['input_tokens'],17)
        self.assertEqual(len(self.calls()),1)
        argv = self.calls()[0]['args']
        self.assertNotIn(prompt, argv)
        self.assertIn('--sandbox', argv)
        self.assertNotIn('--dangerously-bypass-approvals-and-sandbox',argv)
        record = Path(result['record'])
        self.assertNotIn(prompt,record.read_text())
        self.assertEqual(record.stat().st_mode & 0o777, 0o600)

    def test_ambiguous_request_automatically_classifies_then_uses_selected_worker(self):
        result = self.command('complex task')
        self.assertEqual(result['selected'],{'model':'gpt-6-astra','effort':'max'})
        calls = self.calls()
        self.assertEqual(len(calls),2)
        self.assertIn('--output-schema',calls[0]['args'])
        self.assertIn('--disable',calls[0]['args'])
        self.assertEqual(calls[1]['args'][calls[1]['args'].index('--model')+1],'gpt-6-astra')
        self.assertIn('model_reasoning_effort="max"',calls[1]['args'])
        self.assertNotIn('--sandbox',calls[1]['args'])

    def test_snapshot_context_is_identical_for_classifier_and_worker(self):
        self.mode('mutate_context')
        path = self.root/'context.txt'
        path.write_text('original context')
        self.command('--context-file',str(path),'routine task')
        calls = self.calls()
        self.assertIn('original context',calls[0]['stdin'])
        self.assertIn('original context',calls[1]['stdin'])
        self.assertNotIn('new source bytes',calls[1]['stdin'])

    def test_missing_context_and_unsupported_pair_do_not_start_a_worker(self):
        for args in [('계속해줘',),('--model','absent','--effort','low','task'),
                     ('--rules-only','unknown task'),('--context-file','absent.txt','task')]:
            result = self.command(*args,expected=2)
            self.assertFalse(result['task_executed'])
        self.assertEqual(self.calls(),[])

    def test_catalog_and_classifier_failures_do_not_start_worker(self):
        self.mode('catalog_error')
        self.assertFalse(self.command('task',expected=2)['task_executed'])
        self.mode('classifier_error')
        result = self.command('task',expected=2)
        self.assertEqual(result['status'],'classifier_error')
        self.assertEqual(len(self.calls()),1)
        self.assertIn('--output-schema',self.calls()[0]['args'])

    def test_worker_errors_are_not_retried_or_accepted_as_completed(self):
        for mode in ('exit_error','failure_event','incomplete','missing_response','malformed','mismatch',
                     'deep_json','fifo_response'):
            with self.subTest(mode=mode):
                self.mode(mode)
                result = self.command('--model','gpt-6-luna','--effort','low','task',expected=2)
                self.assertEqual(result['status'],'execution_failed')
                self.assertNotIn('SYNTHETIC_SECRET',json.dumps(result))
        self.assertEqual(len(self.calls()),8)

    def test_timeout_and_excess_output_end_promptly(self):
        for mode, options in [('timeout',['--task-timeout','0.15']),
                              ('output_limit',['--max-output-bytes','1024'])]:
            self.mode(mode)
            start=time.monotonic()
            result=self.command('--model','gpt-6-luna','--effort','low',*options,'task',expected=2)
            self.assertLess(time.monotonic()-start,5)
            self.assertIn(result['error'],('timeout','output_limit'))

    def test_unobserved_configuration_remains_unverified(self):
        self.mode('no_observation')
        result=self.command('--model','gpt-6-luna','--effort','low','task')
        self.assertIsNone(result['observed_configuration'])
        self.assertEqual(result['observation_status'],'unverified')

    def test_recursion_and_invalid_budgets_are_blocked_before_calls(self):
        with patch.dict(os.environ,{'HARNESS_ROUTING_DECISION':'active'}):
            self.assertFalse(self.command('task',expected=2)['task_executed'])
        for args in [('--task-timeout','nan'),('--task-timeout','-1'),('--max-output-bytes','0')]:
            self.assertFalse(self.command(*args,'task',expected=2)['task_executed'])
        self.assertEqual(self.calls(),[])

    def queued(self):
        args=parser().parse_args(['run','--cwd',str(self.project),'--codex',str(self.executable),
                                 'complex task'])
        decision, identifier=enqueue(args)
        self.assertEqual(decision['status'],'ready')
        return identifier,self.project/'.runtime/routing'/identifier

    def test_queue_is_consumed_once_without_reclassification(self):
        identifier,directory=self.queued()
        result=self.command('--request-id',identifier,'--sandbox','read-only')
        self.assertEqual(result['selected']['model'],'gpt-6-astra')
        self.assertEqual(len(self.calls()),2)
        self.assertFalse((directory/'request.json').exists())
        self.command('--request-id',identifier,'--sandbox','read-only',expected=2)
        self.assertEqual(len(self.calls()),2)

    def test_queue_rejects_tampering_expiry_and_unavailable_model(self):
        for variant in ('tamper','expiry','catalog'):
            identifier,directory=self.queued()
            request=directory/'request.json'
            if variant in ('tamper','expiry'):
                value=json.loads(request.read_text())
                if variant=='tamper':value['prompt']='injected prompt'
                else:
                    value['created_at']-=1000
                    value.pop('checksum')
                    value['checksum']=digest(value)
                request.write_text(json.dumps(value))
            else:
                value=catalog_payload()
                value['models']=[m for m in value['models'] if m['slug']!='gpt-6-astra']
                self.catalog.write_text(json.dumps(value))
            result=self.command('--request-id',identifier,'--sandbox','read-only',expected=2)
            self.assertFalse(result['task_executed'])
            self.catalog.write_text(json.dumps(catalog_payload()))
        self.assertEqual(len(self.calls()),3) # only the three classifiers

    def test_queue_requires_host_sandbox_and_refuses_mixed_request(self):
        identifier,directory=self.queued()
        self.command('--request-id',identifier,expected=2)
        self.command('--request-id',identifier,'--sandbox','read-only','new task',expected=2)
        self.assertTrue((directory/'request.json').exists())
        self.assertEqual(len(self.calls()),1)

    def test_symlink_runtime_cannot_redirect_private_records(self):
        outside=self.root/'outside';outside.mkdir()
        (self.project/'.runtime').symlink_to(outside,target_is_directory=True)
        result=self.command('--model','gpt-6-luna','--effort','low','task',expected=2)
        self.assertFalse(result['task_executed'])
        self.assertEqual(list(outside.iterdir()),[])
        self.assertEqual(self.calls(),[])

    @unittest.skipUnless(hasattr(os,'mkfifo'),'POSIX FIFO contract')
    def test_fifo_context_is_rejected_without_waiting_or_model_calls(self):
        path=self.root/'context.fifo'
        os.mkfifo(path)
        result=self.command('--context-file',str(path),'task',expected=2,timeout=3)
        self.assertFalse(result['task_executed'])
        self.assertEqual(self.calls(),[])

    def test_input_over_budget_is_blocked_without_silent_truncation(self):
        result=self.command('-',stdin='x'*(1024*1024+1),expected=2)
        self.assertFalse(result['task_executed'])
        self.assertEqual(self.calls(),[])

    def test_chat_routes_each_turn_and_carries_actual_conversation(self):
        result=subprocess.run([sys.executable,str(SOURCE/'tools/harness/run.py'),'chat',
                               '--cwd',str(self.project),'--codex',str(self.executable)],
                              input='routine task\ncontinue\n/quit\n',capture_output=True,text=True,
                              timeout=10,env=dict(os.environ))
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        calls=self.calls()
        self.assertEqual(len(calls),4)
        self.assertIn('worker response: routine task',calls[-1]['stdin'])
        self.assertIn('continue',calls[-1]['stdin'])

    def hook(self,event):
        output=io.StringIO()
        with patch('sys.stdin',io.StringIO(json.dumps(event))),redirect_stdout(output):
            with patch('harness.routing.hooks.parser') as mocked:
                real=parser()
                original=real.parse_args
                def parse(arguments):
                    return original(arguments[:1]+['--codex',str(self.executable)]+arguments[1:])
                mocked.return_value.parse_args.side_effect=parse
                code=prompt_hook(self.project)
        self.assertEqual(code,0)
        return json.loads(output.getvalue())

    def test_prompt_hook_prepares_once_and_returns_explicit_handoff(self):
        event={'hook_event_name':'UserPromptSubmit','cwd':str(self.project),
               'prompt':'complex task','transcript_path':None}
        value=self.hook(event)
        context=value['hookSpecificOutput']['additionalContext']
        self.assertIn('gpt-6-astra / max',context)
        self.assertIn('--request-id',context)
        self.assertEqual(len(self.calls()),1)
        self.assertIn('--output-schema',self.calls()[0]['args'])

    def test_repository_router_hook_is_not_automatically_registered(self):
        config=tomllib.loads((SOURCE/'.codex/config.toml').read_text())
        hooks=json.loads((SOURCE/'.codex/hooks.json').read_text())
        self.assertTrue(config['features']['hooks'])
        self.assertNotIn('UserPromptSubmit',config.get('hooks',{}))
        self.assertNotIn('UserPromptSubmit',hooks['hooks'])
        self.assertEqual(set(hooks['hooks']),{'SessionStart','PreCompact','Stop'})
        self.assertNotIn('route_prompt.py',json.dumps(hooks))
        result=subprocess.run([sys.executable,str(SOURCE/'tools/harness/route_prompt.py')],
                              input='{"hook_event_name":"invalid"}',text=True,
                              capture_output=True,timeout=5)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['decision'],'block')

    def test_hook_failures_block_and_worker_marker_skips_recursion(self):
        self.assertEqual(self.hook({'hook_event_name':'bad'})['decision'],'block')
        identifier,directory=self.queued()
        record=json.loads((directory/'run.json').read_text())
        record['status']='running'
        (directory/'run.json').write_text(json.dumps(record))
        event={'hook_event_name':'UserPromptSubmit','cwd':str(self.project),'prompt':'task'}
        with patch.dict(os.environ,{'HARNESS_ROUTING_DECISION':identifier,
                                   'HARNESS_ROUTING_ROOT':str(self.project)}):
            value=self.hook(event)
        self.assertIn('already routed',value['hookSpecificOutput']['additionalContext'])
        self.assertEqual(len(self.calls()),1)


if __name__=='__main__':
    unittest.main()
