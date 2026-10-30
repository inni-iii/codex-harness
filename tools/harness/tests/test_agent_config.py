"""Config findings and scanner errors never become an unqualified security pass."""
from pathlib import Path
import json
import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

from _support import SOURCE
from harness import agent_config


class AgentConfigTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="agent-config-test-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / ".codex").mkdir()

    def test_nested_profile_and_unpinned_mcp_are_detected_without_credentials(self):
        (self.root / ".codex/config.toml").write_text('[profiles.demo]\nsandbox_mode="danger-full-access"\napproval_policy="never"\n[mcp_servers.demo]\ncommand="npx"\nargs=["-y","example-mcp"]\n')
        result = agent_config.inspect(self.root)
        self.assertEqual(result["status"], "findings")
        self.assertEqual(len(result["findings"]), 3)

    def test_parse_error_and_missing_external_scanner_are_not_passes(self):
        (self.root / ".codex/config.toml").write_text("broken = [")
        self.assertEqual(agent_config.inspect(self.root)["status"], "incomplete")
        self.assertEqual(agent_config.agentshield(self.root)["status"], "unavailable")

    def test_native_skill_snapshot_is_flattened_without_modifying_source(self):
        path = self.root / ".agents/skills/demo/SKILL.md"
        path.parent.mkdir(parents=True)
        path.write_text("# Reviewed instructions\n")
        with tempfile.TemporaryDirectory() as mirror:
            mapping, hashes = agent_config.snapshot_inputs(self.root, Path(mirror))
            self.assertEqual(mapping["skills/demo.md"], ".agents/skills/demo/SKILL.md")
            self.assertEqual((Path(mirror) / "skills/demo.md").read_bytes(), path.read_bytes())
        self.assertEqual(path.read_text(), "# Reviewed instructions\n")

    def test_external_output_is_sanitized_and_missing_coverage_is_rejected(self):
        report = {"summary": {"filesScanned": 1, "totalFindings": 1, "critical": 0, "high": 1, "medium": 0, "low": 0, "info": 0},
                  "findings": [{"id": "unsafe-hook", "severity": "high", "file": "skills/demo.md", "evidence": "never-copy-this", "description": "never-copy-this"}]}
        result = agent_config.normalize(report, 0, {"skills/demo.md": ".agents/skills/demo/SKILL.md"}, self.root)
        self.assertEqual(result["status"], "findings")
        self.assertNotIn("never-copy-this", str(result))
        report["summary"]["filesScanned"] = 0
        with self.assertRaises(ValueError):
            agent_config.normalize(report, 0, {"skills/demo.md": "source"}, self.root)

    @unittest.skipUnless(shutil.which("node"), "Node not installed")
    def test_real_child_cli_contract_without_model_fix_flags_or_inherited_secrets(self):
        # Authored protocol fixture, not the real AgentShield engine.
        (self.root / ".codex/config.toml").write_text('sandbox_mode="workspace-write"\n')
        package = self.root / agent_config.AGENTSHIELD_PACKAGE
        package.parent.mkdir(parents=True)
        package.write_text(json.dumps({"name": "ecc-agentshield", "version": agent_config.AGENTSHIELD_VERSION}))
        entry = package.parent / "dist/index.js"
        entry.parent.mkdir()
        entry.write_text("""
const path = require('path');
const args = process.argv.slice(2);
if (args.length !== 5 || args[0] !== 'scan' || args[1] !== '--path' || args[3] !== '--format' || args[4] !== 'json' || process.env.HARNESS_TEST_PRIVATE) process.exit(1);
console.log(JSON.stringify({summary: {filesScanned:1,totalFindings:1,critical:0,high:1,medium:0,low:0,info:0}, findings:[{id:'test-rule',severity:'high',file:path.join(args[2],'.codex/config.toml'),evidence:'private-fixture-payload'}]}));
""")
        with patch.dict(os.environ, {"HARNESS_TEST_PRIVATE": "must-not-be-forwarded"}):
            result = agent_config.agentshield(self.root)
        self.assertEqual(result["status"], "findings", result)
        self.assertEqual(result["findings"][0]["path"], ".codex/config.toml")
        self.assertNotIn("private-fixture-payload", str(result))
        package.write_text('{"name":"ecc-agentshield","version":"0.0.0"}')
        self.assertEqual(agent_config.agentshield(self.root)["status"], "incomplete")
