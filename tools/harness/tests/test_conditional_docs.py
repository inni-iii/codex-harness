"""Actual Git-free document comparisons guard the existing flow finish path."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import unittest

from _support import SOURCE
import test_skill_flows as fixture
from harness import cli, flow_catalog, provenance as p, skill_flows as flow


class ConditionalDocs(unittest.TestCase):
    def fixture(self):
        f=fixture.FlowTests(methodName='runTest');f.setUp();self.addCleanup(f.doCleanups)
        f.routes['work'][0]['finish_when']='documents_unchanged'
        fixture.dump_routes(f.root/'.agents/skills/work/routes.toml',f.routes['work'])
        return f

    def finish(self,f):
        return f.act('finish',reason='Internal implementation only; current documentation still describes the accepted behavior.')

    def test_git_free_unchanged_docs_skip_document_nodes_after_verification(self):
        f=self.fixture();self.assertFalse((f.root/'.git').exists());f.start();f.verified_parent()
        result=self.finish(f);self.assertEqual(result['flow_status'],'finished')
        events=p.load(flow.path(f.root,'run'))['events']
        self.assertFalse(any(e['node']=='docs:index' for e in events))
        self.assertEqual(events[-1]['documentation'],'unchanged')
        self.assertEqual(p.load(f.root/'docs/tasks/demo/task.json')['status'],'in_progress')

    def test_same_content_and_task_notes_do_not_require_document_steps(self):
        f=self.fixture();file=f.root/'docs/contract.md';file.write_text('Stable contract');f.start()
        file.write_text(file.read_text());file.touch()
        with (f.root/'docs/tasks/demo/notes.md').open('a') as out:out.write('Progress record only')
        f.verified_parent();self.assertEqual(self.finish(f)['flow_status'],'finished')

    def test_edit_add_delete_rename_and_nonmarkdown_docs_require_continuation(self):
        for change in ['edit','add','delete','rename','schema']:
            with self.subTest(change=change):
                f=self.fixture();file=f.root/'docs/contract.md';file.write_text('Before');f.start()
                if change=='edit':file.write_text('After')
                elif change=='add':(f.root/'docs/new.md').write_text('New contract')
                elif change=='delete':file.unlink()
                elif change=='rename':file.rename(file.with_name('renamed.md'))
                else:(f.root/'docs/schema.json').write_text('{"required":"new"}')
                f.verified_parent();before=flow.path(f.root,'run').read_bytes()
                with self.assertRaises(ValueError):self.finish(f)
                self.assertEqual(flow.path(f.root,'run').read_bytes(),before)
                state=flow.inspect(f.root,'run')['documentation']
                self.assertTrue(state['available']);self.assertTrue(state['changed_paths'])
                self.assertEqual(f.act('move',edge_id='done')['node'],'docs:index')

    def test_missing_reason_and_missing_validation_cannot_skip(self):
        f=self.fixture();f.start();f.steps()
        with self.assertRaises(ValueError):self.finish(f)
        with self.assertRaises(ValueError):f.validate()
        f=self.fixture();f.start();f.verified_parent();before=flow.path(f.root,'run').read_bytes()
        for reason in [None,'',' ']:
            with self.subTest(reason=reason),self.assertRaises(ValueError):f.act('finish',reason=reason)
            self.assertEqual(flow.path(f.root,'run').read_bytes(),before)

    def test_legacy_frame_without_document_baseline_uses_continuation(self):
        f=self.fixture();f.start();file=flow.path(f.root,'run');state=p.load(file)
        state['current'].pop('document_baseline',None);state.pop('integrity');state['integrity']=p.signature(state);p.atomic(file,state)
        f.verified_parent()
        with self.assertRaises(ValueError):self.finish(f)
        self.assertEqual(f.act('move',edge_id='done')['node'],'docs:index')

    def test_retry_and_restart_preserve_unprocessed_document_changes(self):
        for mode in ['retry','restart']:
            with self.subTest(mode=mode):
                f=self.fixture();doc=f.root/'docs/contract.md';doc.write_text('Before');f.start();doc.write_text('After')
                if mode=='retry':
                    f.steps();f.validate(result='failed');f.act('move',edge_id='retry',reason='Repair implementation without losing document changes')
                else:
                    f.act('block',reason='Pause while keeping the original document baseline')
                    f.act('restart',reason='Continue the same authorized work')
                f.verified_parent()
                with self.assertRaises(ValueError):self.finish(f)
                self.assertTrue(flow.inspect(f.root,'run')['documentation']['changed_paths'])

    def test_source_change_after_validation_still_blocks_unchanged_docs_finish(self):
        f=self.fixture();f.start();f.verified_parent();(f.root/'example.py').write_text('changed source')
        with self.assertRaises(ValueError):self.finish(f)

    def test_real_cli_finish_accepts_recorded_reason(self):
        f=self.fixture();f.start();f.verified_parent();output=io.StringIO()
        with redirect_stdout(output):code=cli.main(['flow','finish','run','--reason','Private refactor; no documentation contract changes.'],root=f.root)
        self.assertEqual(code,0,output.getvalue());self.assertEqual(json.loads(output.getvalue())['flow_status'],'finished')

    def test_registered_implementation_routes_offer_conditional_finish(self):
        cat=flow_catalog.load(SOURCE)
        for node in ['python-backend:implement','svelte-frontend:implement','postgres:change','docker-containers:configure','verify-work:repair']:
            with self.subTest(node=node):
                self.assertEqual(cat['nodes'][node].get('finish_when'),'documents_unchanged')
                self.assertFalse(cat['nodes'][node]['finish'])

    def test_invalid_conditional_declarations_are_rejected(self):
        for value in [True,'always','']:
            with self.subTest(value=value):
                f=self.fixture();f.routes['work'][0]['finish_when']=value
                fixture.dump_routes(f.root/'.agents/skills/work/routes.toml',f.routes['work'])
                with self.assertRaises(ValueError):flow_catalog.load(f.root)


if __name__ == '__main__':
    unittest.main()
