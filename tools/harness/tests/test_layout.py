"""Verify the public entrypoint and source-only portability after relocation."""
from pathlib import Path
import json
import shutil
import subprocess
import sys
import tempfile
import unittest

from _support import SOURCE


class PortableLayoutTests(unittest.TestCase):
    def command(self, root, *args, cwd=None):
        result = subprocess.run([sys.executable, str(root / 'tools/harness/run.py'), *args],
                                cwd=cwd or root, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def test_entrypoint_finds_repository_when_started_elsewhere(self):
        with tempfile.TemporaryDirectory(prefix='harness-caller-') as caller:
            result = self.command(SOURCE, 'doctor', cwd=caller)
        self.assertEqual(result['status'], 'passed')

    def test_source_archive_supports_context_generation_and_offline_routing(self):
        with tempfile.TemporaryDirectory(prefix='harness-portable-') as temporary:
            root = Path(temporary) / 'fresh checkout with spaces'
            shutil.copytree(SOURCE, root, ignore=shutil.ignore_patterns(
                '.git', '.venv', '.runtime', '.cache', 'node_modules', '__pycache__'))
            self.assertEqual(self.command(root, 'setup')['status'], 'passed')
            context = self.command(root, 'context', '--kind', 'plan', '--read')
            self.assertTrue(all(d.get('content') for d in context['documents']))
            project = self.command(root, 'project', 'demo', '--goal', 'A real project goal')
            self.assertEqual(project['workflow'], 'docs/projects/demo/workflow.toml')
            self.assertIn('A real project goal', (root / 'docs/projects/demo/brief.md').read_text())
            task = self.command(root, 'task', 'first-step', '--kind', 'research',
                                '--goal', 'Compare options', '--acceptance', 'Cite primary evidence')
            self.assertEqual(task['task'], 'docs/tasks/first-step/task.json')
            self.assertEqual(self.command(root, 'doctor')['status'], 'passed')
            name = 'gpt-6-luna'
            catalog = root / '.runtime/catalog.json'
            catalog.parent.mkdir(exist_ok=True)
            catalog.write_text(json.dumps({'models': [{
                'slug': name, 'visibility': 'list', 'input_modalities': ['text'],
                'default_reasoning_level': 'low',
                'supported_reasoning_levels': [{'effort': 'low'}]}]}))
            self.assertTrue(self.command(root, 'catalog', '--catalog-file', str(catalog)))
            decision = self.command(root, 'route', '--catalog-file', str(catalog),
                                    '--rules-only', '--model', name, '--effort', 'low',
                                    'Change a label')
            self.assertEqual(decision['selected']['model'], name)
            self.assertFalse(decision['task_executed'])

