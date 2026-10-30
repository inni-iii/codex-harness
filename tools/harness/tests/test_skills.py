"""Generated skills are discoverable and failures cannot leave orphan directories."""
from pathlib import Path
import tempfile
import unittest

from _support import SOURCE
from harness import context, knowledge, skills


class SkillCreationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="skill-authoring-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        path = self.root / ".agents/skills/base"
        path.mkdir(parents=True)
        (path / "SKILL.md").write_text('---\nname: base\ndescription: Base workflow\n---\nRead the request.\n')
        (self.root / ".agents/context.toml").write_text('version=1\n[[skills]]\nname="base"\nwhen="Base workflow"\ntopics=["base"]\n')
        config = self.root / "tools/harness/harness.toml"
        config.parent.mkdir(parents=True)
        config.write_text('version=1\n')

    def test_created_skill_is_selected_and_read_for_its_topic(self):
        result = skills.create(self.root, "inspect-retries", "Inspect: retry behavior", "Inspect SDK and wrapper retries.", topics=["retry-check"])
        selected = context.select(self.root, "review", [], ["retry-check"], read=True)
        self.assertIn(result["skill"], {d["path"] for d in selected["documents"]})
        self.assertEqual(skills.validate(self.root / result["skill"])["status"], "passed")

    def test_invalid_conditions_and_overwrite_leave_registry_unchanged(self):
        original = (self.root / ".agents/context.toml").read_bytes()
        with self.assertRaises(ValueError):
            skills.create(self.root, "unsafe", "Task", "Read inputs.", paths=["../outside"])
        self.assertFalse((self.root / ".agents/skills/unsafe").exists())
        with self.assertRaises(ValueError):
            skills.create(self.root, "base", "Overwrite", "New body")
        self.assertEqual((self.root / ".agents/context.toml").read_bytes(), original)

    def test_adopted_common_knowledge_can_become_a_registered_skill(self):
        (self.root / "proof.md").write_text("Checked behavior")
        knowledge.add(self.root, {"id": "retry-check", "title": "Retries", "lesson": "Inspect nested retries.",
                                  "conditions": "External calls", "topics": ["retry-check"]})
        with self.assertRaises(ValueError):
            skills.from_knowledge(self.root, "retry-check", "inspect-retries", "Review retry boundaries")
        knowledge.review(self.root, "retry-check", "adopted", "Checked regression", ["proof.md"])
        result = skills.from_knowledge(self.root, "retry-check", "inspect-retries", "Review retry boundaries")
        self.assertIn("Inspect nested retries", (self.root / result["skill"]).read_text())
        self.assertEqual(context.catalog(self.root)["skills"][-1]["name"], "inspect-retries")
