"""Exercise explanation discovery and project-scoped reads, not prose quality."""
from pathlib import Path
import shutil
import tempfile
import unittest

from _support import SOURCE
from harness import context, skill_flows, tasks, workflows


REF = '.agents/skills/plan-project/references/project-explanation.md'
TEMPLATE = '.agents/skills/plan-project/assets/project-explanation.md.tmpl'


class ProjectExplanation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='project-explanation-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        shutil.copytree(SOURCE / '.agents', self.root / '.agents')
        self.write('tools/harness/harness.toml',
                   'version=1\n[[checks]]\nid="fixture"\n'
                   'command=["{python}","-c","print(1)"]\ncwd="."\npaths=["**"]\n')
        self.write('AGENTS.md', '# Synthetic project fixture\n')

    def write(self, relative, body):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)
        return path

    def selected(self, kind, paths=(), topics=(), workflow=None):
        return {d['path']: d for d in context.select(
            self.root, kind, list(paths), list(topics), workflow=workflow, read=True)['documents']}

    def test_delivery_reads_procedure_without_manual_topics(self):
        for kind in ['plan', 'design', 'implement']:
            with self.subTest(kind=kind):
                docs = self.selected(kind)
                self.assertEqual(docs[REF]['content'], (self.root / REF).read_text())
        for kind in ['research', 'experiment', 'review', 'debug']:
            with self.subTest(unrelated=kind):
                self.assertNotIn(REF, self.selected(kind))

    def test_resume_and_final_review_read_procedure_without_creating_a_guide(self):
        for topic in ['resume', 'handoff', 'project-explanation', 'final-explanation']:
            with self.subTest(topic=topic):
                self.assertIn(REF, self.selected('review', topics=[topic]))
        self.assertFalse((self.root / 'docs').exists())

    def test_existing_request_only_routes_consume_procedure_and_preserve_gates(self):
        tasks.create(self.root, 'sample', 'design', 'Explain the current project', ['Preserve actual evidence'])
        for node in ['plan-project:requirements', 'plan-project:plan',
                     'plan-project:analysis', 'plan-project:design']:
            with self.subTest(node=node):
                run = node.replace(':', '-')
                skill_flows.start(self.root, run, 'sample', node)
                docs = {d['path']: d for d in skill_flows.selected_context(
                    self.root, run, read_contents=True)['documents']}
                self.assertEqual(docs[REF]['content'], (self.root / REF).read_text())
                self.assertEqual(skill_flows.inspect(self.root, run)['node'], node)
                self.assertEqual(skill_flows.inspect(self.root, run)['completed_steps'], [])
        with self.assertRaises(ValueError):
            skill_flows.start(self.root, 'blocked', 'sample', 'python-backend:implement')
        skill_flows.start(self.root, 'verify', 'sample', 'verify-work:inspect')
        docs = {d['path']: d for d in skill_flows.selected_context(
            self.root, 'verify', read_contents=True)['documents']}
        acceptance = '.agents/skills/verify-work/references/acceptance.md'
        self.assertEqual(docs[acceptance]['content'], (self.root / acceptance).read_text())
        self.assertNotIn(REF, docs.keys())

    def test_project_guide_is_scoped_and_reused_at_same_path(self):
        profile = workflows.create(self.root, 'sample', 'Understand a small project').relative_to(self.root).as_posix()
        guide = 'docs/sample/architecture/explanation-guide.md'
        body = (self.root / TEMPLATE).read_text().replace('{{project}}', 'sample')
        self.write(guide, body)
        self.write('docs/sample/architecture/index.md',
                   '# Architecture\n\n[Explanation](explanation-guide.md): current project understanding.\n')
        project_index = self.root / 'docs/sample/index.md'
        project_index.write_text(project_index.read_text() +
                                 '\n[Architecture](architecture/index.md): shared explanations.\n')
        p = self.root / profile
        p.write_text(p.read_text() + '\n[[context.rules]]\n'
                     'topics=["project-explanation","final-explanation","resume","handoff"]\n'
                     'paths=["src/core/**"]\n'
                     f'documents=["{guide}"]\n'
                     'when="Read relevant project explanations and evidence."\n')
        self.assertNotIn(guide, self.selected('research', paths=['src/unrelated.py'], workflow=profile))
        self.assertEqual(self.selected('implement', paths=['src/core/main.py'], workflow=profile)[guide]['content'], body)
        revised = body + '\nObserved input handling; execution remains unverified.\n'
        self.write(guide, revised)
        docs = self.selected('review', topics=['resume'], workflow=profile)
        self.assertEqual(docs[guide]['content'], revised)
        self.assertIn('docs/sample/architecture/index.md', docs)
        self.assertEqual(list((self.root / 'docs/sample').rglob('explanation-guide.md')),
                         [self.root / guide])


if __name__ == '__main__':
    unittest.main()
