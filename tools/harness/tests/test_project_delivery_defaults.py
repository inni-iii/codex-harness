"""Delivery instructions are discoverable without adding execution or approval bypasses."""
from pathlib import Path
import shutil
import tempfile
import unittest

from _support import SOURCE
from harness import context, skill_flows, tasks


CHECKLIST = '.agents/skills/plan-project/references/task-patterns.md'


class ProjectDeliveryDefaults(unittest.TestCase):
    def test_plan_and_implementation_read_checklist_without_manual_topics(self):
        for kind in ['plan', 'implement']:
            with self.subTest(kind=kind):
                docs = {d['path']: d for d in context.select(SOURCE, kind, [], [], read=True)['documents']}
                self.assertIn(CHECKLIST, list(docs))
                self.assertEqual(docs[CHECKLIST]['content'], (SOURCE / CHECKLIST).read_text())
        for kind in ['research', 'review', 'experiment', 'debug']:
            with self.subTest(unrelated=kind):
                docs = {d['path'] for d in context.select(SOURCE, kind, [], [])['documents']}
                self.assertNotIn(CHECKLIST, docs)

    def test_requirements_and_plan_routes_read_checklist_without_starting_implementation(self):
        with tempfile.TemporaryDirectory(prefix='project-delivery-') as directory:
            root = Path(directory).resolve()
            shutil.copytree(SOURCE / '.agents', root / '.agents')
            (root / 'tools/harness').mkdir(parents=True)
            (root / 'tools/harness/harness.toml').write_text('version = 1\n')
            tasks.create(root, 'document', 'design', '이 문서로 계획만 세워줘', ['요구와 첫 기능을 정리한다'])
            for route in ['requirements', 'plan']:
                result = skill_flows.start(root, route, 'document', 'plan-project:' + route)
                self.assertEqual(result['node'], 'plan-project:' + route)
                docs = {d['path']: d for d in skill_flows.selected_context(root, route, read_contents=True)['documents']}
                self.assertIn(CHECKLIST, list(docs))
                self.assertEqual(docs[CHECKLIST]['content'], (root / CHECKLIST).read_text())
                self.assertEqual(skill_flows.inspect(root, route)['node'], 'plan-project:' + route)
            # Reading a delivery checklist does not satisfy implementation's design/alignment gate.
            with self.assertRaises(ValueError):
                skill_flows.start(root, 'implementation', 'document', 'python-backend:implement')
            self.assertEqual(skill_flows.inspect(root, 'requirements')['node'], 'plan-project:requirements')


if __name__ == '__main__':
    unittest.main()
