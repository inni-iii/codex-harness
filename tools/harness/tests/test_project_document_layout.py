"""Project placement and linkage are checked at the actual generation/doctor boundaries."""
from pathlib import Path
import shutil
import tempfile
import unittest

from _support import SOURCE
from harness import doctor, workflows


class ProjectDocumentLayout(unittest.TestCase):
    def test_new_project_uses_direct_docs_namespace(self):
        with tempfile.TemporaryDirectory(prefix='project-placement-') as d:
            root = Path(d).resolve()
            for skill in ['plan-project', 'security-review']:
                shutil.copytree(SOURCE / '.agents/skills' / skill / 'assets',
                                root / '.agents/skills' / skill / 'assets')
            created = workflows.create(root, 'demo', 'Deliver an observed result')
            self.assertEqual(created.relative_to(root).as_posix(), 'docs/demo/workflow.toml')
            self.assertFalse((root / 'docs/projects/demo').exists())

    def test_doctor_rejects_loose_feature_document_in_declared_layout(self):
        with tempfile.TemporaryDirectory(prefix='project-placement-') as d:
            root = Path(d).resolve()
            def write(rel, content):
                p = root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content)
            write('tools/harness/harness.toml', 'version=1\nchecks=[]\n[stack]\nfrontend="svelte"\nbackend="python"\n')
            write('docs/index.md', '- [Demo](demo/index.md): project entry\n')
            write('docs/demo/index.md', '- [Loose](loose.md): feature contract currently misplaced\n')
            write('docs/demo/loose.md', '# Feature contract\n')
            write('docs/demo/workflow.toml', 'version=1\nname="demo"\nstate="draft"\nchecks=[]\n'
                  '[documentation]\nlayout="feature-folders"\n[context]\ndocuments=[]\n')
            errors = doctor.inspect(root)['errors']
            self.assertTrue(any('document placement' in e and 'docs/demo/loose.md' in e for e in errors), errors)


if __name__ == '__main__':
    unittest.main()
