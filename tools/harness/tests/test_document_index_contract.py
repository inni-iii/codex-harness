"""Folder maps must cover actual documents without loading their bodies."""
import importlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from _support import SOURCE
from harness import doctor, tasks, workflows


class IndexContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='index-contract-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def write(self, relative, content):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def audit(self):
        return importlib.import_module('harness.document_indexes').inspect(self.root)

    def test_doctor_rejects_missing_folder_index(self):
        self.write('docs/topic/contract.md', '# Contract\n')
        result = doctor.inspect(self.root)
        self.assertTrue(any('docs/topic/index.md' in error and 'missing' in error for error in result['errors']), result['errors'])

    def test_complete_maps_cover_files_and_child_indexes(self):
        self.write('docs/index.md', '| [Topic](topic/index.md) | API rules and operation decisions |\n')
        self.write('docs/topic/index.md', '| [Contract](contract.md#rule) | API input and error contract |\n')
        self.write('docs/topic/contract.md', '# Rule\n')
        result = self.audit()
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['folders'], 2)

    def test_missing_entry_and_link_only_entry_are_rejected(self):
        self.write('docs/api.md', '# API\n')
        for index in ['# Map\n', '[API](api.md)\n', '| [API](api.md) | [API](api.md) |\n', '| [API](api.md) | TODO |\n']:
            with self.subTest(index=index):
                self.write('docs/index.md', index)
                self.assertTrue(any('api.md' in error for error in self.audit()['errors']))

    def test_code_examples_and_comments_do_not_count_as_entries(self):
        self.write('docs/api.md', '# API\n')
        for block in ['```md\n[API](api.md) API input contract\n```', '~~~markdown\n[API](api.md) API input contract\n~~~', '<!-- [API](api.md) API input contract -->', '`[API](api.md) API input contract`']:
            with self.subTest(block=block):
                self.write('docs/index.md', block)
                self.assertTrue(self.audit()['errors'])

    def test_child_folder_map_is_required_even_without_markdown_files(self):
        self.write('docs/knowledge/catalog.json', '{}')
        self.write('docs/index.md', '# Map\n')
        result = self.audit()
        self.assertTrue(any('docs/knowledge/index.md' in e and 'missing' in e for e in result['errors']))
        self.write('docs/knowledge/index.md', '# Knowledge catalog\n')
        self.assertTrue(any('knowledge/index.md' in e for e in self.audit()['errors']))
        self.write('docs/index.md', '| [Knowledge](knowledge/index.md) | Reviewed reusable rules and their evidence |\n')
        self.assertEqual(self.audit()['errors'], [])

    def test_moved_document_leaves_an_error_until_map_is_updated(self):
        self.write('docs/index.md', '| [Old](old.md) | API input contract |\n')
        self.write('docs/new.md', '# API\n')
        errors = self.audit()['errors']
        self.assertTrue(any('old.md' in e for e in errors))
        self.assertTrue(any('new.md' in e for e in errors))
        self.write('docs/index.md', '| [New](new.md) | API input contract |\n')
        self.assertEqual(self.audit()['errors'], [])

    def test_encoded_spaces_and_explicit_relative_targets_work(self):
        self.write('docs/API contract.md', '# API\n')
        for target in ['./API%20contract.md', '<API contract.md>']:
            with self.subTest(target=target):
                self.write('docs/index.md', f'| [API]({target}) | Request and error contract |\n')
                self.assertEqual(self.audit()['errors'], [])

    def test_program_reads_only_maps_not_document_bodies_and_does_not_write(self):
        self.write('docs/index.md', '| [API](api.md) | API input and failure contract |\n')
        self.write('docs/api.md', 'Unrelated large body\n' * 10000)
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        original = Path.read_text
        def guarded(path, *args, **kwargs):
            self.assertEqual(path.name, 'index.md')
            return original(path, *args, **kwargs)
        with patch.object(Path, 'read_text', guarded):
            self.assertEqual(self.audit()['errors'], [])
        self.assertEqual(before, {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_harness_docs_are_checked_but_generated_runtime_is_not(self):
        self.write('tools/harness/docs/guide.md', '# Guide\n')
        self.write('.runtime/logs/trace.md', '# Generated\n')
        result = self.audit()
        self.assertTrue(any('tools/harness/docs/index.md' in e for e in result['errors']))
        self.assertFalse(any('.runtime' in e for e in result['errors']))

    def test_index_symlink_and_directory_symlink_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix='outside-docs-') as outside:
            target = Path(outside)
            (target / 'private.md').write_text('# Outside\n')
            (self.root / 'docs').mkdir()
            (self.root / 'docs/index.md').symlink_to(target / 'private.md')
            self.assertTrue(self.audit()['errors'])
            (self.root / 'docs/index.md').unlink()
            self.write('docs/index.md', '# Map\n')
            (self.root / 'docs/external').symlink_to(target, target_is_directory=True)
            self.assertTrue(self.audit()['errors'])

    def test_task_creation_writes_map_and_links_parent_without_overwrite(self):
        self.write('docs/index.md', '| [Tasks](tasks/index.md) | Work goals, evidence and handoffs |\n')
        self.write('docs/tasks/index.md', '# Existing map\nPreserve this user note.\n')
        tasks.create(self.root, 'sample', 'implement', 'Observe a real result', ['Actual result'])
        self.assertEqual(self.audit()['errors'], [])
        index = self.root / 'docs/tasks/sample/index.md'
        text = index.read_text()
        self.assertIn('(notes.md)', text)
        self.assertIn('(task.json)', text)
        self.assertIn('Preserve this user note.', (index.parent.parent / 'index.md').read_text())
        before = index.read_bytes()
        with self.assertRaises(FileExistsError):
            tasks.create(self.root, 'sample', 'implement', 'Replacement', ['Actual result'])
        self.assertEqual(index.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
