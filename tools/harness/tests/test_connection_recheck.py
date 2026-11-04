"""Concurrent map registration and worktree metadata are shared boundaries."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import os
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from _support import SOURCE
from harness import core, document_indexes, provenance, tasks


class ConnectionRecheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='connection-recheck-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / 'docs/tasks').mkdir(parents=True)
        (self.root / 'docs/index.md').write_text('- [Tasks](tasks/index.md): Work contracts and evidence\n')
        self.index = self.root / 'docs/tasks/index.md'
        self.index.write_text('# Tasks\nPreserve existing user context.\n')

    def create(self, slug):
        return tasks.create(self.root, slug, 'review', 'Inspect ' + slug, ['Actual observable result'])

    def test_concurrent_task_creation_preserves_both_parent_links(self):
        original = Path.read_text
        barrier = threading.Barrier(2)
        def delayed_read(path, *args, **kwargs):
            content = original(path, *args, **kwargs)
            if path == self.index:
                time.sleep(.15)  # Both old readers capture the same parent map.
            return content
        def create(slug):
            barrier.wait(timeout=3)
            return self.create(slug)
        with patch.object(Path, 'read_text', delayed_read):
            with ThreadPoolExecutor(max_workers=2) as pool:
                list(pool.map(create, ['first', 'second']))
        self.assertEqual(document_indexes.inspect(self.root)['errors'], [])
        text = self.index.read_text()
        self.assertEqual(text.count('(first/index.md)'), 1)
        self.assertEqual(text.count('(second/index.md)'), 1)
        self.assertIn('Preserve existing user context.', text)

    def test_failed_atomic_map_update_preserves_original_and_allows_retry(self):
        before = self.index.read_bytes()
        original = os.replace
        def fail_parent(source, destination, *args, **kwargs):
            if Path(destination) == self.index:
                raise OSError('Synthetic replacement failure')
            return original(source, destination, *args, **kwargs)
        with patch.object(os, 'replace', fail_parent):
            with self.assertRaisesRegex(OSError, 'Synthetic replacement failure'):
                self.create('first')
        self.assertEqual(self.index.read_bytes(), before)
        document_indexes.register_folder(self.root, self.root / 'docs/tasks/first', 'first', 'Inspect first')
        self.create('second')
        self.assertEqual(document_indexes.inspect(self.root)['errors'], [])

    def test_worktree_pointer_is_not_a_source_or_evidence_input(self):
        (self.root / 'module.py').write_text('value = 1\n')
        pointer = self.root / '.git'
        pointer.write_text('gitdir: /nonexistent/fixture/worktree-one\n')
        self.assertNotIn('.git', provenance.snapshot(self.root))
        self.assertNotIn('.git', provenance.executable_snapshot(self.root))
        self.assertIn('module.py', provenance.snapshot(self.root))

    def test_worktree_metadata_changes_do_not_invalidate_source_fingerprint(self):
        source = self.root / 'module.py'
        source.write_text('value = 1\n')
        pointer = self.root / '.git'
        pointer.write_text('gitdir: /nonexistent/fixture/worktree-one\n')
        before = core.fingerprint(self.root)
        pointer.write_text('gitdir: /nonexistent/fixture/worktree-two\n')
        self.assertEqual(core.fingerprint(self.root), before)
        source.write_text('value = 2\n')
        self.assertNotEqual(core.fingerprint(self.root), before)


if __name__ == '__main__':
    unittest.main()
