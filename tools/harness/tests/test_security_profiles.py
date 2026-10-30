"""Exercise design activation and real runner gates using isolated fixtures."""
from __future__ import annotations

from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
from unittest.mock import patch
import tempfile
import unittest

from _support import SOURCE, fixture_security
from harness import checks, workflows
from harness.cli import main
from harness.security_profiles import AREAS


class SecurityProfileTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="security-profile-gate-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        base = self.root / "tools/harness/harness.toml"
        base.parent.mkdir(parents=True)
        base.write_text('version=1\n[[checks]]\nid="fast"\ncommand=["{python}","-c","print(1)"]\npaths=["backend/**"]\n[coverage]\ndocumentation=["*.md"]\n')
        self.relative = "docs/projects/demo/workflow.toml"
        self.file = self.root / self.relative
        self.file.parent.mkdir(parents=True)
        self.reviewed = fixture_security(self.root)
        self.requirement = ('area="authorization"\nstatus="required"\n'
            'description="A different local test identity cannot modify another identity resource."\n'
            'paths=["backend/auth/**"]\nchecks=["security-tests"]\n')
        self.reviewed = self.reviewed.replace(
            'area="authorization"\nstatus="not_applicable"\n'
            'description="This fixture exercises command selection only; no product implementation is tested."\n',
            self.requirement)
        self.xml = '<testsuite><testcase name="fixture-boundary"/></testsuite>'
        self.probe(self.xml)
        self.profile()

    def probe(self, xml):
        # This tests runner/report enforcement, not an actual product's auth.
        code = "from pathlib import Path\nimport sys\nPath('.runtime').mkdir(exist_ok=True)\nPath('.runtime/executed').touch()\n"
        if xml is not None:
            code += f"Path(sys.argv[1]).write_text({xml!r})\n"
        (self.root / "security_probe.py").write_text(code)

    def profile(self, security=None, state="active"):
        self.file.write_text(f'''version=1
name="demo"
state="{state}"
[[checks]]
id="security-tests"
command=["{{python}}","security_probe.py","{{report}}"]
paths=["backend/**"]
test_summary="junit"
tier="full"
run_at=["final"]
''' + (self.reviewed if security is None else security))

    def test_missing_draft_blank_design_allows_development_but_keeps_review_pending(self):
        empty_template = (SOURCE / ".agents/skills/security-review/assets/security-profile.md").read_bytes()
        variants = ["", self.reviewed.replace('state="reviewed"', 'state="draft"'),
                    self.reviewed.replace('assets=["Synthetic command-selection metadata"]', 'assets=[]')]
        for security in variants:
            with self.subTest(security=security):
                self.profile(security)
                loaded = workflows.load(self.root, self.relative)
                self.assertEqual(loaded["security_review"]["state"], "pending")
                result = checks.run(self.root, ["backend/auth/session.py"], workflow=self.relative, full=True)
                self.assertEqual(result["status"], "checks_passed_security_pending")
                self.assertFalse(result["completion_ready"])
        self.profile()
        document = self.file.with_name("security.md")
        document.write_bytes(empty_template)
        digest = hashlib.sha256(empty_template).hexdigest()
        import re
        self.file.write_text(re.sub(r'document_sha256="[a-f0-9]+"', f'document_sha256="{digest}"', self.file.read_text()))
        self.assertEqual(workflows.load(self.root, self.relative)["security_review"]["state"], "pending")

    def test_changed_design_runs_local_tests_but_final_verdict_stays_pending(self):
        loaded = workflows.load(self.root, self.relative)
        self.assertIn("docs/projects/demo/security.md", loaded["context"]["documents"])
        with self.file.with_name("security.md").open("a") as stream:
            stream.write("Another external trust boundary was added.\n")
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["check", "--project", self.relative, "--paths", "backend/auth/session.py"], root=self.root)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())["status"], "checks_passed_security_pending")
        self.assertTrue((self.root / ".runtime/executed").exists())
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["check", "--checkpoint", "final", "--project", self.relative, "--paths", "backend/auth/session.py"], root=self.root)
        self.assertEqual(code, 2)
        self.assertFalse(json.loads(output.getvalue())["completion_ready"])

    def test_all_areas_need_decisions_and_references_must_be_real_tests(self):
        for content in [self.reviewed.replace('area="authorization"', 'area="unknown"'),
                        self.reviewed.replace('area="abuse"', 'area="browser"')]:
            with self.subTest(content=content):
                self.profile(content)
                with self.assertRaises(ValueError):
                    workflows.load(self.root, self.relative)
        for content in [self.reviewed.replace('checks=["security-tests"]', 'checks=[]'),
                        self.reviewed.replace('checks=["security-tests"]', 'checks=["missing-tests"]'),
                        self.reviewed.replace('description="A different local test identity cannot modify another identity resource."', 'description="TODO"')]:
            self.profile(content)
            self.assertEqual(workflows.load(self.root, self.relative)["security_review"]["state"], "pending")
        self.profile()
        self.file.write_text(self.file.read_text().replace('test_summary="junit"', ''))
        self.assertEqual(workflows.load(self.root, self.relative)["security_review"]["state"], "pending")

    def test_security_tests_cannot_use_flaky_opt_out_or_nonbehavioral_coverage(self):
        for field in ('allow_flaky=true', 'covers_behavior=false'):
            self.profile()
            self.file.write_text(self.file.read_text().replace('test_summary="junit"', 'test_summary="junit"\n' + field))
            with self.subTest(field=field):
                self.assertEqual(workflows.load(self.root, self.relative)["security_review"]["state"], "pending")

    def test_missing_assessment_and_unsafe_or_missing_document_are_rejected(self):
        last = self.reviewed.rfind('[[security.controls]]')
        for content in [self.reviewed[:last],
                        self.reviewed.replace('document="docs/projects/demo/security.md"', 'document="docs/projects/demo/missing.md"'),
                        self.reviewed.replace('trust_boundaries=["Local temporary test workspace"]', 'trust_boundaries=[]')]:
            self.profile(content)
            with self.subTest(content=content):
                self.assertEqual(workflows.load(self.root, self.relative)["security_review"]["state"], "pending")
        self.profile(self.reviewed.replace('document="docs/projects/demo/security.md"', 'document="../outside.md"'))
        with self.assertRaises(ValueError):
            workflows.load(self.root, self.relative)

    def test_scoped_pending_auth_does_not_block_unrelated_frontend_but_blocks_auth_closure(self):
        self.profile(self.reviewed.replace('status="required"', 'status="pending"'))
        config = self.root / "tools/harness/harness.toml"
        config.write_text(config.read_text().replace('paths=["backend/**"]', 'paths=["backend/**","frontend/**"]'))
        unrelated = checks.run(self.root, ["frontend/display.ts"], workflow=self.relative, checkpoint="final")
        self.assertEqual(unrelated["status"], "passed")
        self.assertEqual(unrelated["security_review"]["applicable_pending"], [])
        self.assertTrue(unrelated["security_review"]["project_pending"])
        affected = checks.run(self.root, ["backend/auth/session.py"], workflow=self.relative, checkpoint="final")
        self.assertEqual(affected["status"], "checks_passed_security_pending")
        entire = checks.run(self.root, ["frontend/display.ts"], full=True, workflow=self.relative)
        self.assertEqual(entire["status"], "checks_passed_security_pending")

    def test_real_test_failure_is_not_hidden_by_pending_security(self):
        self.profile(self.reviewed.replace('state="reviewed"', 'state="draft"'))
        self.probe('<testsuite><testcase><failure/></testcase></testsuite>')
        result = checks.run(self.root, ["backend/auth/session.py"], workflow=self.relative)
        self.assertEqual(result["status"], "failed")

    def test_path_aliases_cannot_bypass_pending_review_or_required_tests(self):
        aliases = ["backend/other/../auth/session.py", "./backend/auth/session.py", "backend//auth/session.py"]
        for status in ("pending", "required"):
            self.profile(self.reviewed.replace('status="required"', f'status="{status}"'))
            for alias in aliases:
                with self.subTest(status=status, alias=alias):
                    result = checks.run(self.root, [alias], workflow=self.relative, checkpoint="final")
                    self.assertEqual(result["paths"], ["backend/auth/session.py"])
                    if status == "pending":
                        self.assertEqual(result["status"], "checks_passed_security_pending")
                    else:
                        self.assertEqual(result["status"], "passed")
                        self.assertIn("security-tests", [r["check"] for r in result["results"]])

    def test_workflow_alias_still_selects_its_required_security_tests(self):
        result = checks.plan(self.root, ["./" + self.relative], workflow="./" + self.relative)
        self.assertIn("security-tests", [c["id"] for c in result["checks"]])

    def test_case_aliases_on_case_insensitive_filesystems_cannot_bypass_security(self):
        actual = self.root / 'backend/auth/session.py'
        actual.parent.mkdir(parents=True)
        actual.write_text('synthetic fixture')
        if not (self.root / 'BACKEND/AUTH/SESSION.py').exists():
            self.skipTest('filesystem distinguishes case aliases')
        self.profile(self.reviewed.replace('status="required"', 'status="pending"'))
        result = checks.run(self.root, ['backend/AUTH/SESSION.py'], workflow=self.relative, checkpoint='final')
        self.assertEqual(result['status'], 'checks_passed_security_pending')
        self.assertEqual(result['paths'], ['backend/auth/session.py'])

    def test_noncanonical_patterns_cannot_silently_remove_pending_scope(self):
        for pattern in ('backend/./auth/**', './backend/auth/**', 'backend//auth/**', 'backend/auth/'):
            self.profile(self.reviewed.replace('status="required"', 'status="pending"')
                         .replace('paths=["backend/auth/**"]', f'paths=["{pattern}"]'))
            with self.subTest(pattern=pattern), self.assertRaises(ValueError):
                checks.plan(self.root, ['backend/auth/session.py'], workflow=self.relative)

    def test_review_change_immediately_after_planning_cannot_be_a_current_pass(self):
        original_plan = checks.plan
        def change_after_plan(*args, **kwargs):
            result = original_plan(*args, **kwargs)
            document = self.file.with_name('security.md')
            document.write_text(document.read_text() + '\nChanged by another session.')
            return result
        with patch('harness.checks.plan', side_effect=change_after_plan):
            result = checks.run(self.root, ['backend/auth/session.py'], workflow=self.relative)
        self.assertEqual(result['status'], 'stale')
        self.assertFalse(result['completion_ready'])
        self.assertFalse((self.root / '.runtime/executed').exists())

    def test_missing_security_document_keeps_context_readable_and_marks_unavailable(self):
        import shutil
        from harness import context
        shutil.copytree(SOURCE / ".agents", self.root / ".agents")
        self.file.with_name("security.md").unlink()
        result = context.select(self.root, "implement", ["backend/auth/session.py"], ["security"], workflow=self.relative, read=True)
        self.assertEqual(result["security_review"]["state"], "pending")
        document = next(d for d in result["documents"] if d["path"] == "docs/projects/demo/security.md")
        self.assertEqual(document["read_status"], "unavailable")

    def test_required_security_tests_override_normal_tier_and_checkpoint_at_feature(self):
        paths = ["backend/auth/session.py"]
        edit = checks.run(self.root, paths, workflow=self.relative, checkpoint="edit")
        self.assertEqual(edit["status"], "checkpoint_passed")
        self.assertIn("security-tests", edit["deferred_checks"])
        self.assertFalse((self.root / ".runtime/executed").exists())
        feature = checks.run(self.root, paths, workflow=self.relative, checkpoint="feature")
        self.assertEqual(feature["status"], "passed", feature)
        self.assertEqual(feature["deferred_checks"], [])
        self.assertTrue((self.root / ".runtime/executed").exists())
        self.assertIn("required security control: authorization", feature["selection_reasons"]["security-tests"])

    def test_required_security_zero_skipped_failed_or_missing_report_never_passes(self):
        for xml in [None, '<testsuite/>', '<testsuite><testcase><skipped/></testcase></testsuite>',
                    '<testsuite><testcase><failure/></testcase></testsuite>']:
            with self.subTest(xml=xml):
                self.probe(xml)
                result = checks.run(self.root, ["backend/auth/session.py"], workflow=self.relative)
                self.assertEqual(result["status"], "failed")

    def test_unrelated_edit_and_prose_only_edit_avoid_expensive_security_suite(self):
        unrelated = checks.plan(self.root, ["backend/display.py"], workflow=self.relative)
        self.assertEqual({c["id"] for c in unrelated["checks"]}, {"fast"})
        document = checks.plan(self.root, ["docs/projects/demo/security.md"], workflow=self.relative)
        self.assertNotIn("security-tests", {c["id"] for c in document["checks"]})
        self.assertEqual(len(workflows.load(self.root, self.relative)["security"]["controls"]), len(AREAS))

    def test_shared_contract_impact_propagates_pending_review_to_consumers(self):
        self.profile(self.reviewed.replace('status="required"', 'status="pending"'))
        config = self.root / "tools/harness/harness.toml"
        config.write_text(config.read_text().replace('paths=["backend/**"]', 'paths=["backend/**","shared/**"]'))
        with self.file.open("a") as stream:
            stream.write('\n[[impacts]]\npaths=["shared/**"]\nchecks=["security-tests"]\nreason="Shared identity contract affects auth."\n')
        result = checks.run(self.root, ["shared/identity.py"], workflow=self.relative)
        self.assertEqual(result["status"], "checks_passed_security_pending")
        self.assertTrue(result["security_review"]["applicable_pending"])

    def test_draft_remains_available_for_planning_but_is_never_verified(self):
        self.profile(self.reviewed.replace('state="reviewed"', 'state="draft"'), state="draft")
        self.assertEqual(workflows.load(self.root, self.relative)["state"], "draft")
        self.assertEqual(checks.run(self.root, ["backend/auth/session.py"], workflow=self.relative)["status"], "needs_configuration")
