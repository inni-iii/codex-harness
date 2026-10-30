"""Manifest conflicts stop installation instead of silently selecting another manager."""
import json
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

from _support import SOURCE
from harness import environment


class EnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="environment-test-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def node(self, manager=None, locks=("package-lock.json",)):
        data = {"name": "local-fixture", "version": "1.0.0"}
        if manager:
            data["packageManager"] = manager
        (self.root / "package.json").write_text(json.dumps(data))
        for name in locks:
            (self.root / name).write_text("{}")

    def test_read_only_detection_uses_project_lock_and_supports_bun_text_lock(self):
        self.node("bun@1.4.4", ("bun.lock",))
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        result = environment.inspect(self.root)
        self.assertEqual(result["groups"][0]["manager"], "bun")
        self.assertEqual({p.name: p.read_bytes() for p in self.root.iterdir()}, before)

    def test_conflicting_manager_or_lockfiles_cannot_reach_process_execution(self):
        self.node("pnpm@10.0.0")
        with patch("harness.environment.execute") as execute:
            self.assertEqual(environment.install(self.root)["status"], "needs_configuration")
            execute.assert_not_called()
        (self.root / "pnpm-lock.yaml").write_text("lockfileVersion: 9")
        self.assertEqual(environment.inspect(self.root)["status"], "needs_configuration")

    def test_manager_version_mismatch_and_missing_executable_are_not_success(self):
        self.node("npm@10.0.0")
        with patch("harness.environment.shutil.which", return_value=None):
            self.assertEqual(environment.install(self.root)["status"], "unavailable")
        with patch("harness.environment.shutil.which", return_value="npm"), patch(
                "harness.environment.subprocess.run", return_value=subprocess.CompletedProcess([], 0, "11.0.0\n", "")):
            self.assertEqual(environment.install(self.root)["reason"], "package_manager_version_mismatch")

    def test_frozen_install_disables_scripts_and_detects_changed_lock(self):
        self.node()
        def execute(command, **kwargs):
            self.assertIn("ci", command)
            self.assertIn("--ignore-scripts", command)
            self.assertIn("--offline", command)
            (self.root / "package-lock.json").write_text("changed")
            return {"exit_code": 0, "error": None}
        with patch("harness.environment.shutil.which", return_value="npm"), patch(
                "harness.environment.subprocess.run", return_value=subprocess.CompletedProcess([], 0, "11.0.0\n", "")), patch(
                "harness.environment.execute", side_effect=execute):
            self.assertEqual(environment.install(self.root, offline=True)["status"], "stale")

    def test_uv_lock_selection_and_python_manager_conflict(self):
        (self.root / "pyproject.toml").write_text('[project]\nname="fixture"\nversion="1.0.0"\n')
        (self.root / "uv.lock").write_text("version = 1")
        self.assertEqual(environment.inspect(self.root)["groups"][0]["manager"], "uv")
        (self.root / "poetry.lock").write_text("# fixture")
        self.assertEqual(environment.inspect(self.root)["status"], "needs_configuration")

    def test_invalid_manifest_tables_are_rejected_before_install(self):
        (self.root / "pyproject.toml").write_text('project=[]\n')
        with self.assertRaises(ValueError):
            environment.install(self.root)

    def test_path_escape_and_symlink_project_are_rejected(self):
        with self.assertRaises(ValueError):
            environment.inspect(self.root, "../outside")
        with tempfile.TemporaryDirectory() as outside:
            (self.root / "linked").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                environment.inspect(self.root, "linked")

    def test_parent_workspace_cannot_silently_expand_install_scope(self):
        for ecosystem in ("node", "python"):
            with self.subTest(ecosystem=ecosystem), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                child = root / "child"
                child.mkdir()
                if ecosystem == "node":
                    (root / "package.json").write_text('{"workspaces":["child"]}')
                    (child / "package.json").write_text('{"name":"child"}')
                    (child / "package-lock.json").write_text('{}')
                else:
                    (root / "pyproject.toml").write_text('[tool.uv.workspace]\nmembers=["child"]\n')
                    (child / "pyproject.toml").write_text('[project]\nname="child"\nversion="1.0.0"\n')
                    (child / "uv.lock").write_text('version=1')
                with patch("harness.environment.execute") as execute:
                    self.assertEqual(environment.install(root, "child")["status"], "needs_configuration")
                    execute.assert_not_called()

    @unittest.skipUnless(shutil.which("npm"), "npm not installed")
    def test_real_offline_npm_install_preserves_lock_and_does_not_run_lifecycle(self):
        self.node()
        package = json.loads((self.root / "package.json").read_text())
        package["scripts"] = {"preinstall": "node -e \"require('fs').writeFileSync('unexpected-script', 'ran')\""}
        (self.root / "package.json").write_text(json.dumps(package))
        lock = {"name": package["name"], "version": package["version"], "lockfileVersion": 3,
                "requires": True, "packages": {"": {"name": package["name"], "version": package["version"], "hasInstallScript": True}}}
        (self.root / "package-lock.json").write_text(json.dumps(lock))
        before = (self.root / "package-lock.json").read_bytes()
        result = environment.install(self.root, offline=True)
        self.assertEqual(result["status"], "passed", result)
        self.assertEqual((self.root / "package-lock.json").read_bytes(), before)
        self.assertFalse((self.root / "unexpected-script").exists())

    @unittest.skipUnless(shutil.which("uv"), "uv not installed")
    def test_real_offline_uv_sync_uses_project_environment_and_preserves_lock(self):
        (self.root / "pyproject.toml").write_text('[project]\nname="local-fixture"\nversion="1.0.0"\nrequires-python=">=3.11"\n[tool.uv]\npackage=false\n')
        prepared = subprocess.run([shutil.which("uv"), "lock", "--offline", "--python", sys.executable,
                                   "--cache-dir", str(self.root / ".cache/uv")], cwd=self.root,
                                  capture_output=True, text=True, timeout=30)
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        before = (self.root / "uv.lock").read_bytes()
        result = environment.install(self.root, offline=True)
        self.assertEqual(result["status"], "passed", result)
        self.assertEqual((self.root / "uv.lock").read_bytes(), before)
        self.assertTrue((self.root / ".venv/pyvenv.cfg").is_file())
