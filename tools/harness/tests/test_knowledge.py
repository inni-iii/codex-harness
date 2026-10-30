"""Knowledge survives workspaces without promoting unreviewed or stale lessons."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
import shutil
import subprocess
import sys
import io
from contextlib import redirect_stdout

from _support import SOURCE
from harness import knowledge
from harness import context, knowledge_hooks
from harness.provenance import signature
from harness import cli


class KnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="knowledge-test-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "proof.md").write_text("Observed regression and successful correction.\n")

    def spec(self, identity="retry-boundary", project=None):
        return {"id": identity, "title": "Retry boundary", "lesson": "Inspect duplicate side effects before retrying.",
                "conditions": "When changing an external call.", "exclusions": ["Pure local calculations"],
                "project": project, "topics": ["external-api"], "paths": [], "kinds": [], "sources": ["proof.md"]}

    def adopt(self, identity="retry-boundary", project=None):
        knowledge.add(self.root, self.spec(identity, project))
        return knowledge.review(self.root, identity, "adopted", "Regression checked", ["proof.md"])

    def test_empty_reads_do_not_create_storage_or_runtime(self):
        before = list(self.root.rglob("*"))
        self.assertEqual(knowledge.listing(self.root)["entries"], [])
        self.assertEqual(knowledge.selected(self.root, "research", [], []), [])
        self.assertEqual(list(self.root.rglob("*")), before)

    def test_candidate_never_enters_context_and_adoption_needs_evidence(self):
        knowledge.add(self.root, self.spec())
        self.assertFalse(knowledge.selected(self.root, "implement", [], ["external-api"]))
        with self.assertRaises(ValueError):
            knowledge.review(self.root, "retry-boundary", "adopted", "Looks useful")
        knowledge.review(self.root, "retry-boundary", "adopted", "Actual evidence", ["proof.md"])
        self.assertEqual(len(knowledge.selected(self.root, "implement", [], ["external-api"])), 1)

    def test_project_scope_and_current_evidence_control_retrieval(self):
        self.adopt(project="demo")
        self.assertFalse(knowledge.selected(self.root, "implement", [], ["external-api"]))
        self.assertFalse(knowledge.selected(self.root, "implement", [], ["external-api"], "other"))
        self.assertEqual(len(knowledge.selected(self.root, "implement", [], ["external-api"], "demo")), 1)
        (self.root / "proof.md").write_text("Changed evidence\n")
        self.assertFalse(knowledge.selected(self.root, "implement", [], ["external-api"], "demo"))

    def test_supersession_requires_an_adopted_same_scope_replacement(self):
        self.adopt()
        knowledge.add(self.root, self.spec("new-rule"))
        with self.assertRaises(ValueError):
            knowledge.review(self.root, "retry-boundary", "superseded", "New rule", replacement="new-rule")
        knowledge.review(self.root, "new-rule", "adopted", "Verified replacement", ["proof.md"])
        knowledge.review(self.root, "retry-boundary", "superseded", "Replaced", replacement="new-rule")
        self.assertEqual([e["id"] for e in knowledge.selected(self.root, "implement", [], ["external-api"])], ["new-rule"])
        with self.assertRaises(ValueError):
            knowledge.review(self.root, "retry-boundary", "adopted", "Restore", ["proof.md"])

    def test_promotion_creates_a_common_candidate_and_preserves_project_rule(self):
        self.adopt(project="demo")
        knowledge.promote(self.root, "retry-boundary", "common-retry", "Applicable conditions reviewed")
        promoted = knowledge.show(self.root, "common-retry")["entry"]
        self.assertIsNone(promoted["project"])
        self.assertEqual(promoted["state"], "candidate")
        self.assertEqual(promoted["origin"]["promoted_from"], "retry-boundary")
        self.assertEqual(knowledge.show(self.root, "retry-boundary")["entry"]["state"], "adopted")

    def test_export_import_is_previewable_and_downgrades_external_adoption(self):
        self.adopt()
        knowledge.export(self.root, "bundle.json")
        other = self.root / "other"
        other.mkdir()
        (other / "bundle.json").write_bytes((self.root / "bundle.json").read_bytes())
        before = list(other.rglob("*"))
        result = knowledge.import_bundle(other, "bundle.json", dry_run=True)
        self.assertEqual(result["status"], "planned")
        self.assertEqual(list(other.rglob("*")), before)
        knowledge.import_bundle(other, "bundle.json")
        entry = knowledge.show(other, "retry-boundary")["entry"]
        self.assertEqual(entry["state"], "candidate")
        self.assertEqual(entry["origin"]["state"], "adopted")
        self.assertEqual(knowledge.import_bundle(other, "bundle.json")["skipped"], ["retry-boundary"])

    def test_conflicting_import_and_invalid_checksum_do_not_change_catalog(self):
        self.adopt()
        knowledge.export(self.root, "bundle.json")
        path = self.root / knowledge.CATALOG
        before = path.read_bytes()
        bundle_path = self.root / "bundle.json"
        bundle = json.loads(bundle_path.read_text())
        bundle["payload"]["entries"][0]["lesson"] = "A different rule"
        bundle["sha256"] = signature(bundle["payload"])
        bundle_path.write_text(json.dumps(bundle))
        self.assertEqual(knowledge.import_bundle(self.root, "bundle.json")["status"], "needs_review")
        self.assertEqual(path.read_bytes(), before)
        bundle["sha256"] = "invalid"
        bundle_path.write_text(json.dumps(bundle))
        with self.assertRaises(ValueError):
            knowledge.import_bundle(self.root, "bundle.json")
        self.assertEqual(path.read_bytes(), before)

    def test_credentials_unsafe_ids_and_injected_state_are_rejected_without_writes(self):
        for field, value in [("id", "../escape"), ("state", "adopted"),
                             ("lesson", "TOKEN=" + "synthetic-" + "q" * 32)]:
            spec = self.spec()
            spec[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                knowledge.add(self.root, spec)
        self.assertFalse((self.root / knowledge.CATALOG).exists())

    def test_existing_writer_is_not_overwritten(self):
        lock = self.root / ".runtime/knowledge.lock"
        lock.parent.mkdir()
        lock.write_text("another writer")
        with self.assertRaises(ValueError):
            knowledge.add(self.root, self.spec())
        self.assertEqual(lock.read_text(), "another writer")

    def test_malformed_stored_review_metadata_is_rejected_at_catalog_boundary(self):
        self.adopt()
        path = self.root / knowledge.CATALOG
        valid = json.loads(path.read_text())
        for field, value in (("state", None), ("history", ["invalid event"])):
            data = deepcopy(valid)
            if value is None:
                data["entries"][0].pop(field)
            else:
                data["entries"][0][field] = value
            path.write_text(json.dumps(data))
            with self.subTest(field=field), self.assertRaises(ValueError):
                knowledge.catalog(self.root)

    def test_symlink_store_is_rejected(self):
        with tempfile.TemporaryDirectory() as outside:
            (self.root / "docs").mkdir()
            (self.root / "docs/knowledge").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                knowledge.add(self.root, self.spec())
            self.assertFalse(list(Path(outside).iterdir()))

    def test_context_reads_only_matching_reviewed_entry_from_portable_catalog(self):
        shutil.copytree(SOURCE / ".agents", self.root / ".agents")
        config = self.root / "tools/harness/harness.toml"
        config.parent.mkdir(parents=True)
        config.write_text('version=1\n[stack]\nfrontend="svelte"\nbackend="python"\n')
        self.adopt()
        chosen = context.select(self.root, "implement", [], ["external-api"], read=True)
        entries = [d for d in chosen["documents"] if d.get("entry_id")]
        self.assertEqual(len(entries), 1)
        self.assertEqual(json.loads(entries[0]["content"])["lesson"], self.spec()["lesson"])
        other = context.select(self.root, "research", [], [], read=True)
        self.assertFalse(any(d.get("entry_id") for d in other["documents"]))

    def test_hook_checkpoints_keep_metadata_and_never_copy_prompt_payloads(self):
        path = self.root / "docs/tasks/demo/task.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"status": "in_progress", "private": "must never be copied"}))
        output = knowledge_hooks.handle(self.root, {"hook_event_name": "PreCompact", "session_id": "session-one",
                                                    "prompt": "must never be copied", "trigger": "manual"})
        self.assertEqual(output, {})
        files = list((self.root / ".runtime/knowledge-events").glob("*.json"))
        self.assertEqual(len(files), 1)
        text = files[0].read_text()
        self.assertNotIn("must never be copied", text)
        self.assertNotIn("session-one", text)
        self.assertEqual(json.loads(text)["tasks"][0]["state"], "in_progress")

    def hook_context(self):
        config = self.root / "tools/harness/harness.toml"
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text('version=1\n')
        result = knowledge_hooks.handle(self.root, {"hook_event_name": "SessionStart", "session_id": "bounded-context", "source": "compact"})
        return result["hookSpecificOutput"]["additionalContext"]

    def test_hook_retains_complete_applicability_and_exclusions(self):
        spec = self.spec()
        spec["topics"] = ["learning"]
        knowledge.add(self.root, spec)
        knowledge.review(self.root, spec["id"], "adopted", "Verified bounded rule", ["proof.md"])
        text = self.hook_context()
        self.assertIn(spec["lesson"], text)
        self.assertIn(spec["conditions"], text)
        self.assertIn(spec["exclusions"][0], text)

    def test_hook_oversized_rule_is_referenced_without_partial_instruction(self):
        spec = self.spec()
        spec.update(topics=["learning"], lesson="long-instruction " * 800,
                    conditions="condition " * 800, exclusions=["Never omit this restriction."])
        knowledge.add(self.root, spec)
        knowledge.review(self.root, spec["id"], "adopted", "Source identity checked", ["proof.md"])
        text = self.hook_context()
        self.assertIn("knowledge show " + spec["id"], text)
        self.assertNotIn("long-instruction", text)
        self.assertLessEqual(len(text), 8000)

    def test_malformed_state_and_history_actions_are_value_errors(self):
        valid = self.adopt()["entry"]
        for value in ([], {}, 42):
            for field in ("state", "history_action"):
                bad = deepcopy(valid)
                if field == "state":
                    bad["state"] = value
                else:
                    bad["history"][0]["action"] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    knowledge.validate(bad)

    def test_import_checks_serialized_storage_size_and_preserves_previous_catalog(self):
        knowledge.add(self.root, self.spec())
        original = (self.root / knowledge.CATALOG).read_bytes()
        entries = [{"id": "rule-" + str(i), "title": "Fixture", "lesson": "Reviewed rule", "conditions": "Fixture use",
                    "topics": ["tag"] * 100, "state": "candidate", "history": [], "evidence": []} for i in range(1200)]
        payload = {"version": 1, "entries": entries}
        bundle = self.root / "large-bundle.json"
        bundle.write_text(json.dumps({"payload": payload, "sha256": signature(payload)}))
        self.assertLess(bundle.stat().st_size, knowledge.LIMIT)
        with self.assertRaises(ValueError):
            knowledge.import_bundle(self.root, "large-bundle.json")
        self.assertEqual((self.root / knowledge.CATALOG).read_bytes(), original)
        self.assertEqual(knowledge.listing(self.root)["count"], 1)

    def test_real_hook_stdin_contract_for_compact_context_and_input_limit(self):
        shutil.copytree(SOURCE / "tools/harness/harness", self.root / "tools/harness/harness")
        script = self.root / "tools/harness/scripts/knowledge-hook.py"
        script.parent.mkdir()
        shutil.copyfile(SOURCE / "tools/harness/scripts/knowledge-hook.py", script)
        (self.root / "tools/harness/harness.toml").write_text('version=1\n')
        event = {"hook_event_name": "PreCompact", "session_id": "contract-session", "trigger": "auto"}
        result = subprocess.run([sys.executable, str(script)], input=json.dumps(event), capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {})
        event.update(hook_event_name="SessionStart", source="compact")
        result = subprocess.run([sys.executable, str(script)], input=json.dumps(event), capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)["hookSpecificOutput"]
        self.assertEqual(output["hookEventName"], "SessionStart")
        self.assertIn("PreCompact.json", output["additionalContext"])
        result = subprocess.run([sys.executable, str(script)], input="x" * 65537, capture_output=True, text=True, timeout=5)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("x" * 100, result.stdout + result.stderr)

    def test_cli_lifecycle_registers_retrievable_skill_and_rejects_duplicate(self):
        shutil.copytree(SOURCE / ".agents", self.root / ".agents")
        config = self.root / "tools/harness/harness.toml"
        config.parent.mkdir(parents=True)
        config.write_text('version=1\n')
        (self.root / "spec.json").write_text(json.dumps(self.spec()))
        def invoke(arguments):
            output = io.StringIO()
            with redirect_stdout(output):
                code = cli.main(arguments, root=self.root)
            return code, json.loads(output.getvalue())
        self.assertEqual(invoke(["knowledge", "add", "spec.json"])[0], 0)
        self.assertEqual(invoke(["knowledge", "review", "retry-boundary", "--state", "adopted", "--reason", "Verified fixture", "--evidence", "proof.md"])[0], 0)
        self.assertEqual(invoke(["knowledge", "search", "side effects"])[1]["count"], 1)
        self.assertEqual(invoke(["skill", "from-knowledge", "retry-boundary", "inspect-retry-boundary", "--description", "Inspect retry side effects"])[0], 0)
        self.assertEqual(invoke(["skill", "validate", "inspect-retry-boundary"])[0], 0)
        result = invoke(["context", "--kind", "implement", "--topic", "external-api", "--read"])
        self.assertTrue(any(d.get("entry_id") == "retry-boundary" for d in result[1]["documents"]))
        self.assertTrue(any(d["path"] == ".agents/skills/inspect-retry-boundary/SKILL.md" for d in result[1]["documents"]))
        self.assertNotEqual(invoke(["knowledge", "add", "spec.json"])[0], 0)


if __name__ == "__main__":
    unittest.main()
