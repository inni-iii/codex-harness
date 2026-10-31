"""Specialist ownership and selective reading retain verification boundaries."""
from pathlib import Path
import tempfile
import unittest

from _support import SOURCE
from harness import context


class SkillScopeTests(unittest.TestCase):
    def selected(self, kind, paths=(), topics=()):
        records = context.select(SOURCE, kind, list(paths), list(topics), read=True)["documents"]
        self.assertTrue(all(r.get("content") for r in records))
        return {r["path"] for r in records}

    def test_learning_has_one_specialist_owner_without_loading_planning(self):
        selected = self.selected("research", topics=["learning"])
        self.assertIn(".agents/skills/maintain-knowledge/SKILL.md", selected)
        self.assertIn(".agents/skills/maintain-knowledge/references/learning.md", selected)
        self.assertNotIn(".agents/skills/plan-project/SKILL.md", selected)

    def test_plain_doc_edit_and_review_keep_common_checks_without_code_manuals(self):
        detailed = {f".agents/skills/verify-work/references/{name}.md" for name in
                    ["follow-through", "checkpoints", "impact", "evidence", "review"]}
        for kind, topic in [("implement", "docs-organization"), ("review", "docs-check")]:
            with self.subTest(kind=kind):
                selected = self.selected(kind, ["docs/README.md"], [topic])
                self.assertIn(".agents/skills/verify-work/SKILL.md", selected)
                self.assertIn(".agents/skills/docs-maintenance/SKILL.md", selected)
                self.assertFalse(selected & detailed, selected & detailed)

    def test_code_review_retains_detailed_impact_evidence_and_followthrough(self):
        selected = self.selected("review", ["backend/service.py"])
        for name in ["follow-through", "checkpoints", "impact", "evidence", "review"]:
            self.assertIn(f".agents/skills/verify-work/references/{name}.md", selected)

    def test_code_under_docs_is_not_misclassified_as_a_prose_only_change(self):
        selected = self.selected("implement", ["docs/examples/handler.py"])
        self.assertIn(".agents/skills/verify-work/references/impact.md", selected)
        self.assertIn(".agents/skills/verify-work/references/evidence.md", selected)

    def test_explicit_defect_and_completion_requests_keep_their_procedures(self):
        for kind, topic in [("research", "regression"), ("review", "completion")]:
            with self.subTest(topic=topic):
                selected = self.selected(kind, ["docs/README.md"], [topic])
                self.assertIn(".agents/skills/verify-work/references/follow-through.md", selected)
        selected = self.selected("research", ["docs/tasks/demo/task.json"])
        self.assertIn(".agents/skills/verify-work/references/completion.md", selected)
        review = self.selected("research", ["docs/tasks/demo/review.json"])
        self.assertIn(".agents/skills/verify-work/references/follow-through.md", review)

    def test_auth_changes_still_include_security_review(self):
        selected = self.selected("implement", ["backend/auth/session.py"])
        self.assertIn(".agents/skills/security-review/references/application.md", selected)
        self.assertIn(".agents/skills/verify-work/references/impact.md", selected)

    def test_visual_evidence_and_browser_failures_are_read_from_e2e(self):
        visual = self.selected("review", topics=["visual-check"])
        self.assertIn(".agents/skills/e2e-testing/references/visual.md", visual)
        browser = self.selected("debug", ["frontend/e2e/save.spec.ts"], ["playwright"])
        for name in ["scenarios", "setup", "writing", "failures"]:
            self.assertIn(f".agents/skills/e2e-testing/references/{name}.md", browser)

        ui = self.selected("implement", ["frontend/Card.svelte"])
        self.assertNotIn(".agents/skills/e2e-testing/references/writing.md", ui)

    def test_research_does_not_inherit_code_completion_manuals_from_paths_alone(self):
        selected = self.selected("research", ["backend/service.py"])
        self.assertNotIn(".agents/skills/verify-work/references/review.md", selected)
        self.assertNotIn(".agents/skills/verify-work/references/follow-through.md", selected)

    def test_code_review_stage_guard_does_not_expand_an_implementation_request(self):
        for kind in ["implement", "debug"]:
            with self.subTest(kind=kind):
                selected = self.selected(kind, ["frontend/Card.svelte"], ["code-review"])
                self.assertNotIn(".agents/skills/verify-work/references/review.md", selected)
                self.assertIn(".agents/skills/verify-work/references/impact.md", selected)

    def test_required_kind_metadata_rejects_invalid_or_empty_guards(self):
        with tempfile.TemporaryDirectory(prefix="skill-kind-") as directory:
            root = Path(directory)
            (root / ".agents/skills/base/references").mkdir(parents=True)
            (root / ".agents/skills/base/SKILL.md").write_text("# Base\n")
            (root / ".agents/skills/base/references/detail.md").write_text("# Detail\n")
            for value in ['"review"', '[]', '["unknown"]', 'true']:
                with self.subTest(value=value):
                    (root / ".agents/context.toml").write_text('version=1\n[[skills]]\nname="base"\n'
                        'when="Common flow"\ntopics=["base"]\n[[skills.references]]\n'
                        'file=".agents/skills/base/references/detail.md"\nwhen="Detail"\n'
                        'topics=["detail"]\nrequires_kinds=' + value + '\n')
                    with self.assertRaises(ValueError):
                        context.catalog(root)

