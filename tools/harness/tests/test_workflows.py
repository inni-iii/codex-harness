"""Observe selective reading, project integration and verification failure modes."""
from __future__ import annotations

import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import shutil
import tempfile
import unittest

from _support import SOURCE, fixture_security

from harness import checks, context, workflows
from harness.cli import main
from harness.core import manifest



class ProjectWorkspace(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="harness-project-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "tools/harness").mkdir(parents=True, exist_ok=True)
        (self.root / "tools/harness/harness.toml").write_text('''version = 1
[stack]
frontend = "svelte"
backend = "python"
[[checks]]
id = "harness"
command = ["{python}", "-c", "print('harness')"]
paths = ["tools/harness/harness/**"]
[coverage]
documentation = ["*.md"]
''')

    def profile(self, state="active"):
        folder = self.root / "docs/projects/demo"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "brief.md").write_text("# Project requirements\nKeep existing item listing.\n")
        (folder / "backend.md").write_text("# Backend domain rule\nOnly the owner may edit.\n")
        path = folder / "workflow.toml"
        path.write_text(f'''version = 1
name = "demo"
state = "{state}"
[context]
documents = ["docs/projects/demo/brief.md"]
[[context.rules]]
paths = ["backend/**"]
documents = ["docs/projects/demo/backend.md"]
[[checks]]
id = "backend"
command = ["{{python}}", "-c", "print('backend')"]
paths = ["backend/**"]
[[checks]]
id = "frontend"
command = ["{{python}}", "-c", "print('frontend')"]
paths = ["frontend/**"]
[[checks]]
id = "app-smoke"
command = ["{{python}}", "-c", "print('connected')"]
paths = ["smoke/**"]
always = true
[[checks]]
id = "full-e2e"
command = ["{{python}}", "-c", "print('full-e2e')"]
paths = ["frontend/**", "backend/**"]
tier = "full"
[[impacts]]
paths = ["backend/schema.py", "shared/**"]
checks = ["frontend", "backend"]
reason = "Shared API contract affects both consumers."
''')
        with path.open("a") as stream:
            stream.write(fixture_security(self.root))
        return path.relative_to(self.root).as_posix()


class WorkflowTests(ProjectWorkspace):
    def test_local_backend_change_selects_smoke_without_full_frontend_suite(self):
        result = checks.plan(self.root, ["backend/service.py"], workflow=self.profile())
        self.assertEqual({c["id"] for c in result["checks"]}, {"backend", "app-smoke"})
        self.assertFalse(result["uncovered_paths"])
        self.assertIn("shared smoke", result["selection_reasons"]["app-smoke"][0])

    def test_shared_api_change_expands_checks_to_other_consumers(self):
        result = checks.plan(self.root, ["backend/schema.py"], workflow=self.profile())
        self.assertEqual({c["id"] for c in result["checks"]}, {"backend", "frontend", "app-smoke"})
        self.assertIn("Shared API", result["selection_reasons"]["frontend"][0])

    def test_smoke_and_impact_do_not_hide_unmapped_source(self):
        result = checks.run(self.root, ["shared/new-code.py"], workflow=self.profile())
        self.assertEqual(result["status"], "needs_configuration")
        self.assertEqual(result["uncovered_paths"], ["shared/new-code.py"])
        self.assertFalse(result["results"])

    def test_full_expands_registered_checks_and_config_change_rechecks_profile(self):
        profile = self.profile()
        full = checks.plan(self.root, ["backend/service.py"], full=True, workflow=profile)
        self.assertIn("full-e2e", {c["id"] for c in full["checks"]})
        changed = checks.plan(self.root, [profile], workflow=profile)
        self.assertEqual({c["id"] for c in changed["checks"]}, {"harness", "backend", "frontend", "app-smoke"})

    def test_draft_cannot_be_reported_as_verified(self):
        result = checks.run(self.root, ["backend/service.py"], workflow=self.profile("draft"))
        self.assertEqual(result["status"], "needs_configuration")
        self.assertTrue(result["configuration_pending"])

    def test_active_project_is_used_by_default_and_override_is_validated(self):
        profile = self.profile()
        with (self.root / "tools/harness/harness.toml").open("a") as stream:
            stream.write(f'\n[project]\nworkflow = "{profile}"\n')
        result = checks.run(self.root, ["backend/service.py"])
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["workflow"], profile)
        with self.assertRaises(ValueError):
            checks.plan(self.root, [], workflow="../external.toml")

    def test_profiles_reject_duplicate_checks_unknown_impacts_and_missing_docs(self):
        profile = self.profile()
        file = self.root / profile
        original = file.read_text()
        for text in [original.replace('id = "backend"', 'id = "harness"'),
                     original.replace('checks = ["frontend", "backend"]', 'checks = ["typo"]'),
                     original.replace('docs/projects/demo/brief.md', 'docs/projects/demo/missing.md')]:
            file.write_text(text)
            with self.assertRaises(ValueError):
                manifest(self.root, profile)

    def test_docs_only_change_does_not_force_app_smoke(self):
        result = checks.plan(self.root, ["docs/projects/demo/brief.md"], workflow=self.profile())
        self.assertEqual(result["checks"], [])

    def test_generator_creates_portable_draft_without_overwriting(self):
        shutil.copytree(SOURCE / ".agents/skills/plan-project/assets", self.root / ".agents/skills/plan-project/assets")
        shutil.copytree(SOURCE / ".agents/skills/security-review/assets", self.root / ".agents/skills/security-review/assets")
        file = workflows.create(self.root, "new-topic", "Create an example project")
        profile = workflows.load(self.root, str(file.relative_to(self.root)))
        self.assertEqual(profile["state"], "draft")
        self.assertEqual(profile["checks"], [])
        self.assertNotIn(str(SOURCE), file.read_text())
        self.assertIn("Create an example project", file.with_name("brief.md").read_text())
        self.assertTrue(file.with_name("security.md").is_file())
        self.assertIn("docs/projects/new-topic/security.md", profile["context"]["documents"])
        with self.assertRaises(FileExistsError):
            workflows.create(self.root, "new-topic", "different")

    def test_generator_rejects_project_parent_symlink_outside_repository(self):
        with tempfile.TemporaryDirectory(prefix="harness-outside-") as outside:
            (self.root / "docs").mkdir()
            (self.root / "docs/projects").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                workflows.create(self.root, "new-topic", "Keep writes inside the repository")
            self.assertEqual(list(Path(outside).iterdir()), [])

    def test_reading_rules_reject_typos_empty_conditions_and_outside_paths(self):
        profile = self.profile()
        file = self.root / profile
        original = file.read_text()
        doc = 'documents = ["docs/projects/demo/backend.md"]\n'
        cases = [doc, 'kinds = ["implementation"]\n' + doc,
                 'topics = "auth"\n' + doc,
                 'topics = ["auth"]\ndocuments = []\n',
                 'paths = ["../secret"]\n' + doc,
                 'topic = ["auth"]\npaths = ["backend/**"]\n' + doc]
        for rule in cases:
            with self.subTest(rule=rule):
                file.write_text(original + '\n[[context.rules]]\n' + rule)
                with self.assertRaises(ValueError):
                    workflows.load(self.root, profile)


class ContextTests(ProjectWorkspace):
    def setUp(self):
        super().setUp()
        shutil.copytree(SOURCE / ".agents", self.root / ".agents")
        shutil.copy2(SOURCE / "AGENTS.md", self.root / "AGENTS.md")

    def test_research_reads_actual_selected_evidence_not_all_technical_manuals(self):
        result = context.select(self.root, "research", [], [], read=True)
        paths = {d["path"] for d in result["documents"]}
        self.assertIn(".agents/skills/research/references/evidence.md", paths)
        self.assertFalse(any("python-backend" in p or "svelte" in p for p in paths))
        self.assertTrue(all(d["content"] == (self.root / d["path"]).read_text() for d in result["documents"]))

    def test_postgres_migration_path_and_sql_performance_topic_select_specific_guidance(self):
        migration = context.select(self.root, "review", ["backend/alembic/versions/add_field.py"], [], read=True)
        docs = {d["path"]: d for d in migration["documents"]}
        self.assertIn(".agents/skills/postgres/SKILL.md", docs)
        for name in ["migrations", "testing"]:
            path = f".agents/skills/postgres/references/{name}.md"
            self.assertEqual(docs[path]["content"], (self.root / path).read_text())
        self.assertNotIn(".agents/skills/postgres/references/performance.md", docs)
        query = context.select(self.root, "review", ["queries/list.sql"], ["query-performance"])
        paths = {d["path"] for d in query["documents"]}
        self.assertIn(".agents/skills/postgres/references/performance.md", paths)
        self.assertNotIn(".agents/skills/postgres/references/migrations.md", paths)

    def test_rag_guidance_is_conditional_and_does_not_load_database_manuals(self):
        reference = ".agents/skills/research/references/retrieval.md"
        plain = context.select(self.root, "research", [], [])
        self.assertNotIn(reference, {d["path"] for d in plain["documents"]})
        selected = context.select(self.root, "research", [], ["rag"], read=True)
        docs = {d["path"]: d for d in selected["documents"]}
        self.assertEqual(docs[reference]["content"], (self.root / reference).read_text())
        self.assertFalse(any("/postgres/" in p or "/python-backend/" in p for p in docs))

    def test_frontend_race_adds_async_reference_but_not_unselected_sveltekit(self):
        result = context.select(self.root, "debug", ["frontend/src/Search.svelte"], ["async"])
        paths = {d["path"] for d in result["documents"]}
        self.assertIn(".agents/skills/svelte-frontend/references/state-and-lifecycle.md", paths)
        self.assertNotIn(".agents/skills/svelte-frontend/references/data-and-forms.md", paths)
        self.assertFalse(any("python-backend" in p for p in paths))

    def test_project_context_always_includes_brief_and_matching_domain_rules(self):
        profile = self.profile()
        result = context.select(self.root, "implement", ["backend/service.py"], [], workflow=profile, read=True)
        docs = {d["path"]: d.get("content") for d in result["documents"]}
        self.assertIn("docs/projects/demo/brief.md", docs)
        self.assertIn("Only the owner", docs["docs/projects/demo/backend.md"])
        frontend = context.select(self.root, "implement", ["frontend/New.svelte"], [], workflow=profile)
        self.assertNotIn("docs/projects/demo/backend.md", {d["path"] for d in frontend["documents"]})

    def test_unknown_topic_missing_reference_and_outside_docs_fail(self):
        with self.assertRaises(ValueError):
            context.select(self.root, "research", [], ["typo"])
        with self.assertRaises(ValueError):
            context.select(self.root, "research", ["../secret.md"], [])
        (self.root / ".agents/skills/research/references/evidence.md").unlink()
        with self.assertRaises(ValueError):
            context.select(self.root, "research", [], [])

    def test_cli_returns_selected_file_contents(self):
        output = io.StringIO()
        with redirect_stdout(output):
            result = main(["context", "--kind", "research", "--read"], root=self.root)
        self.assertEqual(result, 0)
        self.assertIn("content", json.loads(output.getvalue())["documents"][0])

    def add_project_reading_rule(self, profile, text):
        file = self.root / profile
        file.write_text(file.read_text() + '\n[[context.rules]]\n' + text)

    def test_resume_reads_actual_checkpoint_without_code_path_and_debug_reads_lessons(self):
        profile = self.profile()
        folder = self.root / "docs/projects/demo"
        (folder / "checkpoint.md").write_text("# Checkpoint\nBrowser check is still unverified.\n")
        (folder / "lessons.md").write_text("# Lesson\nA timer cleanup alone did not stop in-flight requests.\n")
        self.add_project_reading_rule(profile,
            'topics = ["resume"]\ndocuments = ["docs/projects/demo/checkpoint.md"]\nwhen = "Restore the last checkpoint."\n')
        self.add_project_reading_rule(profile,
            'kinds = ["debug"]\ndocuments = ["docs/projects/demo/lessons.md"]\n')
        resumed = context.select(self.root, "plan", [], ["resume"], workflow=profile, read=True)
        docs = {d["path"]: d for d in resumed["documents"]}
        self.assertIn("still unverified", docs["docs/projects/demo/checkpoint.md"]["content"])
        self.assertIn("Restore the last checkpoint.", docs["docs/projects/demo/checkpoint.md"]["reasons"])
        self.assertNotIn("docs/projects/demo/lessons.md", docs)
        debug = context.select(self.root, "debug", [], [], workflow=profile, read=True)
        self.assertIn("docs/projects/demo/lessons.md", {d["path"] for d in debug["documents"]})
        self.assertNotIn("docs/projects/demo/checkpoint.md", {d["path"] for d in debug["documents"]})

    def test_project_topic_namespace_does_not_leak_to_other_requests(self):
        profile = self.profile()
        self.add_project_reading_rule(profile,
            'topics = ["refund-policy"]\ndocuments = ["docs/projects/demo/backend.md"]\n')
        selected = context.select(self.root, "research", [], ["refund-policy"], workflow=profile)
        self.assertIn("docs/projects/demo/backend.md", {d["path"] for d in selected["documents"]})
        with self.assertRaises(ValueError):
            context.select(self.root, "research", [], ["refund-policy"])

    def test_declared_project_topic_is_available_without_activating_unrelated_rules(self):
        profile = self.profile()
        file = self.root / profile
        file.write_text(file.read_text().replace('[context]\n', '[context]\ntopics = ["data-inspection"]\n', 1))
        result = context.select(self.root, "research", [], ["data-inspection"], workflow=profile)
        selected = {d["path"] for d in result["documents"]}
        self.assertIn("docs/projects/demo/brief.md", selected)
        self.assertNotIn("docs/projects/demo/backend.md", selected)
        with self.assertRaises(ValueError):
            context.select(self.root, "research", [], ["data-inspection"])

    def test_project_kind_topic_and_path_are_independent_alternatives(self):
        profile = self.profile()
        self.add_project_reading_rule(profile,
            'kinds = ["review"]\ntopics = ["domain-check"]\npaths = ["domain/**"]\n'
            'documents = ["docs/projects/demo/backend.md"]\n')
        for kind, paths, topics in [("review", [], []), ("research", [], ["domain-check"]),
                                    ("implement", ["domain/rules.py"], [])]:
            with self.subTest(kind=kind, paths=paths, topics=topics):
                result = context.select(self.root, kind, paths, topics, workflow=profile)
                self.assertIn("docs/projects/demo/backend.md", {d["path"] for d in result["documents"]})

    def test_auth_change_and_explicit_upload_request_select_security(self):
        for paths, topics in [(["backend/auth/session.py"], []), ([], ["uploads"])]:
            with self.subTest(paths=paths, topics=topics):
                result = context.select(self.root, "implement", paths, topics)
                self.assertIn(".agents/skills/security-review/references/application.md",
                              {d["path"] for d in result["documents"]})

    def test_small_ui_change_does_not_load_all_new_workflows(self):
        result = context.select(self.root, "implement", ["frontend/src/Label.svelte"], [])
        selected = {d["path"] for d in result["documents"]}
        for name in ["security.md", "review.md", "handoff.md", "learning.md", "quality-requirements.md",
                     "observability.md", "external-calls.md"]:
            self.assertFalse(any(p.endswith('/' + name) for p in selected), name)

    def test_review_planning_learning_and_external_call_topics_select_their_procedures(self):
        cases = [("review", ["code-review"], "verify-work/references/review.md"),
                 ("plan", [], "plan-project/references/quality-requirements.md"),
                 ("research", ["learning"], "maintain-knowledge/references/learning.md"),
                 ("implement", ["observability"], "python-backend/references/observability.md"),
                 ("implement", ["llm"], "python-backend/references/external-calls.md")]
        for kind, topics, file in cases:
            with self.subTest(kind=kind, topics=topics):
                result = context.select(self.root, kind, [], topics, read=True)
                selected = {d["path"]: d for d in result["documents"]}
                self.assertIn('.agents/skills/' + file, selected)
                self.assertEqual(selected['.agents/skills/' + file]["content"],
                                 (self.root / '.agents/skills' / file).read_text())


class JUnitTests(ProjectWorkspace):
    def test_xml_declarations_depth_and_node_budget_fail_before_unbounded_parsing(self):
        samples = ['<!DOCTYPE testsuite [<!ENTITY x "synthetic">]><testsuite><testcase name="&x;"/></testsuite>',
                   '<testsuite>' * 66 + '<testcase/>' + '</testsuite>' * 66]
        for xml in samples:
            with self.subTest(length=len(xml)):
                self.configure(xml)
                self.assertEqual(checks.run(self.root, ['probe.py'])['status'], 'failed')

    def configure(self, xml=None, code=0):
        script = "import pathlib, sys\n"
        if xml is not None:
            script += f"pathlib.Path(sys.argv[1]).write_text({xml!r})\n"
        script += f"raise SystemExit({code})\n"
        (self.root / "probe.py").write_text(script)
        (self.root / "tools/harness").mkdir(parents=True, exist_ok=True)
        (self.root / "tools/harness/harness.toml").write_text('''version = 1
[[checks]]
id = "tests"
command = ["{python}", "probe.py", "{report}"]
paths = ["**"]
test_summary = "junit"
cacheable = true
''')

    def test_nested_suite_totals_are_not_double_counted(self):
        self.configure('<testsuites tests="2"><testsuite tests="2"><testcase name="pass"/><testcase name="skip"><skipped/></testcase></testsuite></testsuites>')
        result = checks.run(self.root, ["probe.py"])
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["results"][0]["test_count"], 2)
        self.assertEqual(result["results"][0]["skipped_count"], 1)
        self.assertTrue(Path(result["results"][0]["test_report"]).is_file())

    def test_missing_malformed_zero_skipped_and_xml_failure_are_never_passes(self):
        samples = [None, '<broken>', '<testsuite/>',
                   '<testsuite><testcase><skipped/></testcase></testsuite>',
                   '<testsuite><testcase><failure>bad</failure></testcase></testsuite>',
                   '<testsuite errors="1"><testcase/></testsuite>']
        for xml in samples:
            with self.subTest(xml=xml):
                self.configure(xml)
                self.assertEqual(checks.run(self.root, ["probe.py"])["status"], "failed")

    def test_previous_report_cannot_substitute_for_missing_fresh_report(self):
        self.configure('<testsuite><testcase/></testsuite>')
        first = checks.run(self.root, ["probe.py"])
        self.assertEqual(first["status"], "passed")
        self.configure(None)
        second = checks.run(self.root, ["probe.py"])
        self.assertEqual(second["results"][0]["status"], "invalid_test_report")

    def test_nonzero_exit_cannot_be_overridden_by_green_xml(self):
        self.configure('<testsuite><testcase/></testsuite>', code=3)
        result = checks.run(self.root, ["probe.py"])
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["results"][0]["exit_code"], 3)

    def test_negative_cancelled_and_inconsistent_junit_counts_are_not_passes(self):
        samples = [
            '<testsuite tests="1" errors="-1" failures="1"><testcase/></testsuite>',
            '<testsuite tests="-1"><testcase/></testsuite>',
            '<testsuite tests="2"><testcase/></testsuite>',
            '<testsuite skipped="1"><testcase/></testsuite>',
            '<testsuite tests="1" failures="0"><testcase><failure/></testcase></testsuite>',
        ]
        for xml in samples:
            with self.subTest(xml=xml):
                self.configure(xml)
                result = checks.run(self.root, ["probe.py"])
                self.assertEqual(result["status"], "failed")

    def test_junit_configuration_requires_fresh_report_placeholder(self):
        self.configure()
        file = self.root / "tools/harness/harness.toml"
        file.write_text(file.read_text().replace(', "{report}"', ''))
        with self.assertRaises(ValueError):
            manifest(self.root)


if __name__ == "__main__":
    unittest.main()
