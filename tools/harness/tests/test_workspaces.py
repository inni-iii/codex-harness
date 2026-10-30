"""Real isolated Git repositories exercise isolation, conflicts and merged behavior."""
from __future__ import annotations

import io
from contextlib import redirect_stdout
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from _support import SOURCE
from harness import workspaces
from harness.cli import main
from harness.core import fingerprint


@unittest.skipUnless(shutil.which('git'), 'Git required for worktree integration')
class WorkspacesTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='harness-workspaces-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.git('init', '-b', 'main')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('config', 'commit.gpgsign', 'false')
        self.git('config', 'core.autocrlf', 'false')
        (self.root / '.gitignore').write_text('.worktrees/\n.runtime/\n__pycache__/\n')
        (self.root / 'feature.py').write_text('value = 1\n')
        (self.root / 'caller.py').write_text('from feature import value\nassert value == 1\n')
        tools = self.root / 'tools/harness'
        tools.mkdir(parents=True)
        (tools / 'harness.toml').write_text('''version = 1
[[checks]]
id = "behavior"
command = ["{python}", "caller.py"]
paths = ["feature.py", "caller.py"]
cacheable = false
[coverage]
documentation = ["*.md", ".gitignore", "tools/harness/harness.toml"]
''')
        self.git('add', '.')
        self.git('commit', '-m', 'fixture baseline')
        self.base = self.git('rev-parse', 'HEAD')

    def git(self, *args, root=None):
        result = subprocess.run(['git', *args], cwd=root or self.root,
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def branch(self, name, file, text):
        self.git('switch', '-c', name, self.base)
        (self.root / file).write_text(text)
        self.git('add', file)
        self.git('commit', '-m', name)
        self.git('switch', 'main')

    def prepare(self, name='combine', source='source', target='target'):
        return workspaces.prepare(self.root, name, source, target, 'Complete one user outcome',
                                  ['Preserve target behavior', 'Preserve source behavior'])

    def test_start_isolates_files_and_preserves_main_branch_and_index(self):
        before = self.git('ls-files', '--stage')
        data = workspaces.start(self.root, 'one-outcome', 'HEAD', 'Create and find a saved item', ['frontend/**', 'backend/**'])
        isolated = self.root / data['workspace']
        (isolated / 'feature.py').write_text('value = 2\n')
        self.assertEqual((self.root / 'feature.py').read_text(), 'value = 1\n')
        self.assertEqual(self.git('branch', '--show-current'), 'main')
        self.assertEqual(self.git('ls-files', '--stage'), before)
        self.assertTrue(workspaces.status(isolated)['isolated'])
        with self.assertRaisesRegex(ValueError, 'Already in a linked worktree'):
            workspaces.start(isolated, 'nested', 'HEAD', 'Nested', ['frontend/**'])

    def test_missing_baseline_dirty_source_and_nonignored_directory_refuse_without_losing_work(self):
        fresh = self.root / 'fresh'
        fresh.mkdir()
        self.git('init', '-b', 'main', root=fresh)
        with self.assertRaisesRegex(ValueError, 'committed base'):
            workspaces.start(fresh, 'new', 'HEAD', 'Outcome', ['frontend/**'])
        (self.root / 'feature.py').write_text('unfinished\n')
        with self.assertRaisesRegex(ValueError, 'uncommitted changes'):
            workspaces.start(self.root, 'dirty', 'HEAD', 'Outcome', ['frontend/**'])
        self.assertEqual((self.root / 'feature.py').read_text(), 'unfinished\n')

    def test_nonignored_worktree_path_is_rejected(self):
        (self.root / '.gitignore').write_text('.runtime/\n')
        self.git('add', '.gitignore')
        self.git('commit', '-m', 'remove ignore in fixture')
        with self.assertRaisesRegex(ValueError, 'gitignore'):
            workspaces.start(self.root, 'new', 'HEAD', 'Outcome', ['frontend/**'])

    def test_text_conflict_is_preserved_for_review_and_cannot_run_as_success(self):
        self.branch('target', 'feature.py', 'value = 2\n')
        self.branch('source', 'feature.py', 'value = 3\n')
        before = self.git('rev-parse', 'HEAD')
        data = self.prepare()
        self.assertEqual(data['status'], 'needs_resolution')
        self.assertEqual(data['overlapping_paths'], ['feature.py'])
        self.assertIn('<<<<<<<', (self.root / data['workspace'] / 'feature.py').read_text())
        self.assertEqual(workspaces.verify(self.root, 'combine')['status'], 'needs_resolution')
        self.assertEqual(self.git('rev-parse', 'HEAD'), before)
        self.assertIn('feature.py', (self.root / data['review']).read_text())

    def test_staged_conflict_markers_are_still_rejected(self):
        self.branch('target', 'feature.py', 'value = 2\n')
        self.branch('source', 'feature.py', 'value = 3\n')
        data = self.prepare()
        directory = self.root / data['workspace']
        self.git('add', 'feature.py', root=directory)
        self.assertEqual(workspaces.unresolved(directory), [])
        self.assertEqual(workspaces.verify(self.root, 'combine')['status'], 'needs_resolution')

    def test_clean_text_merge_with_broken_shared_contract_fails_real_merged_behavior(self):
        # Each branch works alone: target changes a value; source asserts old semantics.
        self.branch('target', 'feature.py', 'value = 2\n')
        # Make target individually valid as well, changing a second caller line.
        self.git('switch', 'target')
        (self.root / 'caller.py').write_text('from feature import value\nassert value > 0\n')
        self.git('add', 'caller.py')
        self.git('commit', '-m', 'target contract')
        self.git('switch', 'main')
        self.branch('source', 'source_check.py', 'from feature import value\nassert value == 1\n')
        self.git('switch', 'source')
        config = self.root / 'tools/harness/harness.toml'
        config.write_text(config.read_text().replace('"caller.py"]', '"source_check.py"]', 1))
        self.git('add', 'tools/harness/harness.toml')
        self.git('commit', '-m', 'source behavior check')
        self.git('switch', 'main')
        data = self.prepare()
        self.assertEqual(data['status'], 'prepared')
        self.assertEqual(data['overlapping_paths'], [])
        result = workspaces.verify(self.root, 'combine')
        self.assertEqual(result['status'], 'needs_configuration')
        # Register the newly added test itself, then run the actual incompatible combination.
        directory = self.root / data['workspace']
        config = directory / 'tools/harness/harness.toml'
        config.write_text(config.read_text().replace('"feature.py", "caller.py"]', '"feature.py", "caller.py", "source_check.py"]'))
        result = workspaces.verify(self.root, 'combine')
        self.assertEqual(result['status'], 'failed', result)
        self.assertFalse(result['product_accepted'])

    def test_success_still_requires_review_and_covers_both_work_units(self):
        self.branch('target', 'target.md', '# Target outcome\n')
        self.branch('source', 'source.md', '# Source outcome\n')
        data = self.prepare()
        plan = workspaces.verify(self.root, 'combine', plan=True)
        self.assertEqual(set(plan['paths']), {'target.md', 'source.md'})
        result = workspaces.verify(self.root, 'combine', full=True)
        self.assertEqual(result['status'], 'checks_passed_review_pending', result)
        self.assertTrue(result['review_required'])
        self.assertFalse(result['product_accepted'])
        self.assertEqual(self.git('rev-parse', 'HEAD', root=self.root / data['workspace']), self.git('rev-parse', 'target'))

    def test_source_change_after_preparation_invalidates_integration(self):
        self.branch('target', 'target.md', '# Target\n')
        self.branch('source', 'source.md', '# Source\n')
        self.prepare()
        self.git('switch', 'source')
        (self.root / 'source.md').write_text('# Changed since preparation\n')
        self.git('add', 'source.md')
        self.git('commit', '-m', 'new source revision')
        self.git('switch', 'main')
        self.assertEqual(workspaces.verify(self.root, 'combine')['status'], 'stale')

    def test_dirty_input_cannot_be_silently_omitted(self):
        self.branch('target', 'target.md', '# Target\n')
        self.branch('source', 'source.md', '# Source\n')
        self.git('switch', 'source')
        (self.root / 'source.md').write_text('not committed\n')
        with self.assertRaisesRegex(ValueError, 'uncommitted changes'):
            self.prepare()

    def test_review_workspace_files_do_not_change_main_source_fingerprint(self):
        before = fingerprint(self.root)
        (self.root / '.worktrees/review').mkdir(parents=True)
        (self.root / '.worktrees/review/feature.py').write_text('arbitrary review edits\n')
        self.assertEqual(before, fingerprint(self.root))

    def test_cli_reports_baseline_requirement_without_auto_commit(self):
        fresh = self.root / 'fresh'
        fresh.mkdir()
        self.git('init', '-b', 'main', root=fresh)
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(['session', 'start', 'feature', '--goal', 'Outcome', '--scope', 'frontend/**'], root=fresh)
        self.assertEqual(code, 2)
        self.assertIn('committed base', json.loads(output.getvalue())['error'])
