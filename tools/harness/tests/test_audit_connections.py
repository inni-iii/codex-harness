"""Cross-module checks of task handoff, selective reading and execution contracts."""
from pathlib import Path
import tempfile
import unittest

from _support import SOURCE
from harness import checks, context, evidence, tasks
from harness.core import validate_checks


class AuditConnectionTests(unittest.TestCase):
    def test_review_metadata_can_continue_without_hiding_code_in_task_folders(self):
        with tempfile.TemporaryDirectory(prefix='harness-connection-') as directory:
            root = Path(directory).resolve()
            task = tasks.create(root, 'research', 'research', 'Compare evidence', ['Explain the conclusion'])
            review = evidence.review_template(root, 'research')['review']
            paths = [task.relative_to(root).as_posix(), review]
            plan = checks.plan(SOURCE, paths)
            self.assertEqual(plan['uncovered_paths'], [])
            self.assertEqual({c['id'] for c in plan['checks']}, {'doctor', 'secret-patterns'})
            self.assertEqual(checks.plan(SOURCE, ['docs/tasks/research/helper.py'])['uncovered_paths'],
                             ['docs/tasks/research/helper.py'])
            self.assertEqual(checks.plan(SOURCE, ['docs/tasks/research/unknown.json'])['uncovered_paths'],
                             ['docs/tasks/research/unknown.json'])

    def test_pure_design_can_read_a_smaller_scope_without_browser_execution_guidance(self):
        design = context.select(SOURCE, 'design', [], ['ui-design'])
        implementation = context.select(SOURCE, 'implement', ['frontend/Form.svelte'], ['ui'])
        design_files = {item['path'] for item in design['documents']}
        implementation_files = {item['path'] for item in implementation['documents']}
        self.assertIn('.agents/skills/design-first/references/contracts.md', design_files)
        self.assertIn('.agents/skills/plan-project/references/quality-requirements.md', design_files)
        self.assertNotIn('.agents/skills/e2e-testing/SKILL.md', design_files)
        self.assertIn('.agents/skills/e2e-testing/SKILL.md', implementation_files)
        self.assertIn('.agents/skills/verify-work/SKILL.md', implementation_files)
        self.assertLess(len(design_files), len(implementation_files))

    def test_research_task_completion_discovers_evidence_without_language_suites(self):
        selected = context.select(SOURCE, 'research', ['docs/tasks/research/task.json'], [])
        paths = {item['path'] for item in selected['documents']}
        self.assertIn('.agents/skills/research/SKILL.md', paths)
        self.assertIn('.agents/skills/verify-work/references/completion.md', paths)
        self.assertNotIn('.agents/skills/python-backend/SKILL.md', paths)
        self.assertNotIn('.agents/skills/e2e-testing/SKILL.md', paths)

    def test_unknown_execution_or_ordering_fields_are_not_silently_ignored(self):
        check = {'id': 'example', 'command': ['{python}', '-c', "print('ok')"], 'paths': ['**']}
        for key, value in [('time_out', 1), ('run_after', ['setup']), ('parallel', True), ('cacheble', True)]:
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'unknown check fields'):
                validate_checks(SOURCE, [check | {key: value}])
