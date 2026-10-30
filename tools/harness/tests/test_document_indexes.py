"""Indexes guide selective reading without recursively expanding their links."""
from pathlib import Path
import shutil
import tempfile
import unittest

from _support import SOURCE
from harness import context, workflows


class DocumentIndexTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="document-index-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / ".agents/skills/base").mkdir(parents=True)
        (self.root / ".agents/skills/base/SKILL.md").write_text("# Base\n")
        (self.root / ".agents/context.toml").write_text(
            'version=1\n[[skills]]\nname="base"\nwhen="Only explicit topic"\ntopics=["base"]\n')
        (self.root / "tools/harness").mkdir(parents=True)
        (self.root / "tools/harness/harness.toml").write_text("version=1\n")
        (self.root / "AGENTS.md").write_text("# Rules\n")

    def write(self, relative, text):
        p = self.root / relative
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        return p

    def selected(self, **kwargs):
        return context.select(self.root, "research", [], [], read=True, **kwargs)["documents"]

    def test_root_index_is_read_after_rules_without_expanding_linked_documents(self):
        self.write("docs/index.md", "# Map\n[API](api.md) [Ops](ops.md)\n")
        self.write("docs/api.md", "# API\n")
        self.write("docs/ops.md", "Unrelated operations details.\n" * 1000)
        records = self.selected()
        self.assertEqual([r["path"] for r in records], ["AGENTS.md", "docs/index.md"])
        self.assertIn("[API]", records[1]["content"])

    def test_selected_profile_index_is_read_once_before_mandatory_and_matching_docs(self):
        self.write("docs/index.md", "# Root\n")
        self.write("profiles/demo/index.md", "# Project map\n")
        self.write("profiles/demo/brief.md", "# Required brief\n")
        self.write("profiles/demo/api.md", "# API contract\n")
        self.write("profiles/demo/ops.md", "# Ops\n" + "irrelevant " * 1000)
        self.write("profiles/demo/workflow.toml", '''version=1
name="demo"
state="draft"
[context]
documents=["profiles/demo/index.md","profiles/demo/brief.md"]
[[context.rules]]
topics=["api"]
documents=["profiles/demo/api.md"]
[[context.rules]]
topics=["deploy"]
documents=["profiles/demo/ops.md"]
''')
        records = context.select(self.root, "research", [], ["api"],
                                 workflow="profiles/demo/workflow.toml", read=True)["documents"]
        paths = [r["path"] for r in records]
        self.assertEqual(paths, ["AGENTS.md", "docs/index.md", "profiles/demo/index.md",
                                 "profiles/demo/brief.md", "profiles/demo/api.md"])
        self.assertEqual(paths.count("profiles/demo/index.md"), 1)

    def test_missing_indexes_preserve_legacy_explicit_document_selection(self):
        self.write("profiles/legacy/brief.md", "# Required\n")
        self.write("profiles/legacy/workflow.toml", '''version=1
name="legacy"
state="draft"
[context]
documents=["profiles/legacy/brief.md"]
''')
        records = self.selected(workflow="profiles/legacy/workflow.toml")
        self.assertEqual([r["path"] for r in records], ["AGENTS.md", "profiles/legacy/brief.md"])

    def test_automatic_index_cannot_resolve_outside_the_repository(self):
        with tempfile.TemporaryDirectory(prefix="outside-index-") as outside:
            target = Path(outside) / "private.md"
            target.write_text("Outside the selected repository")
            (self.root / "docs").mkdir()
            (self.root / "docs/index.md").symlink_to(target)
            with self.assertRaises(ValueError):
                self.selected()

    def test_project_generation_creates_a_linked_index_without_planned_document_stubs(self):
        for name in ("plan-project", "security-review"):
            shutil.copytree(SOURCE / f".agents/skills/{name}", self.root / f".agents/skills/{name}")
        profile = workflows.create(self.root, "demo", "A chosen subject")
        project = profile.parent
        index = project / "index.md"
        self.assertTrue(index.is_file())
        text = index.read_text()
        self.assertIn("[프로젝트 개요](brief.md)", text)
        self.assertIn("[보안 설계](security.md)", text)
        self.assertIn("[워크플로 설정](workflow.toml)", text)
        self.assertIn("선행 작업", text)
        loaded = workflows.load(self.root, profile.relative_to(self.root).as_posix())
        self.assertIn("docs/projects/demo/index.md", loaded["context"]["documents"])
        self.assertEqual({p.name for p in project.iterdir()},
                         {"index.md", "brief.md", "security.md", "workflow.toml"})
        before = {p.name: p.read_bytes() for p in project.iterdir()}
        with self.assertRaises(FileExistsError):
            workflows.create(self.root, "demo", "Replacement")
        self.assertEqual(before, {p.name: p.read_bytes() for p in project.iterdir()})

    def test_index_never_replaces_the_required_security_document(self):
        from _support import fixture_security
        security = fixture_security(self.root, "profiles/demo")
        self.write("profiles/demo/index.md", "# Project map\n")
        self.write("profiles/demo/workflow.toml", 'version=1\nname="demo"\nstate="draft"\n'
                   '[context]\ndocuments=[]\n' + security)
        records = self.selected(workflow="profiles/demo/workflow.toml")
        paths = [r["path"] for r in records]
        self.assertIn("profiles/demo/security.md", paths)
        self.assertIn("profiles/demo/index.md", paths)
        self.assertLess(paths.index("profiles/demo/index.md"), paths.index("profiles/demo/security.md"))
