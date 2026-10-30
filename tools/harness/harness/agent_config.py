"""Narrow Codex checks plus an optional pinned AgentShield CLI adapter."""
from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import tempfile
import tomllib

from .core import strict_json
from .provenance import load, local_file, sha
from .security import _environment, _execute

AGENTSHIELD_VERSION = "1.6.0"
AGENTSHIELD_PACKAGE = "tools/harness/security/node_modules/ecc-agentshield/package.json"


def inspect(root):
    findings, inputs, incomplete = [], [], []
    def finding(path, rule, severity="high"):
        findings.append({"path": path, "rule": rule, "severity": severity})
    relative = ".codex/config.toml"
    try:
        path = local_file(root, relative)
        if path.stat().st_size > 2 * 1024 * 1024:
            raise ValueError("oversized config")
        data = tomllib.loads(path.read_text())
        inputs.append({"path": relative, "sha256": sha(path)})
        profiles = data.get("profiles", {})
        if not isinstance(profiles, dict):
            raise ValueError("invalid profiles")
        for scope in [data, *profiles.values()]:
            if not isinstance(scope, dict):
                raise ValueError("invalid profile")
            if scope.get("sandbox_mode") == "danger-full-access":
                finding(relative, "codex-sandbox-full-access")
            if scope.get("approval_policy") == "never":
                finding(relative, "codex-approval-never", "medium")
            servers = scope.get("mcp_servers", {})
            if not isinstance(servers, dict):
                raise ValueError("invalid MCP servers")
            for server in servers.values():
                if not isinstance(server, dict):
                    raise ValueError("invalid MCP server")
                args = server.get("args", [])
                if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
                    raise ValueError("invalid MCP arguments")
                command = Path(str(server.get("command", ""))).name
                if command in {"npx", "bunx", "pnpx"} and any(a in {"-y", "--yes"} for a in args):
                    spec = next((a for a in args if not a.startswith("-")), "")
                    if not re.search(r"@\d+\.\d+\.\d+(?:$|[-+])", spec):
                        finding(relative, "mcp-automatic-unpinned-package")
                env_vars = server.get("env_vars", [])
                if not isinstance(env_vars, list) or not all(isinstance(v, str) for v in env_vars):
                    raise ValueError("invalid MCP environment names")
                if "*" in env_vars:
                    finding(relative, "mcp-all-environment-forwarded")
    except (OSError, ValueError, TypeError):
        incomplete.append(relative)
    relative = ".codex/hooks.json"
    if (root / relative).exists():
        try:
            path = local_file(root, relative)
            data = load(path, 2 * 1024 * 1024)
            hooks = data.get("hooks")
            if not isinstance(hooks, dict):
                raise ValueError("invalid hooks")
            supported = {"SessionStart", "SessionEnd", "PreToolUse", "PostToolUse", "PermissionRequest", "PreCompact",
                         "PostCompact", "Stop", "Interrupt", "UserPromptSubmit", "SubagentStart", "SubagentStop"}
            for event, groups in hooks.items():
                if event not in supported or not isinstance(groups, list):
                    raise ValueError("unsupported hook event")
                for group in groups:
                    if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                        raise ValueError("invalid hook matcher group")
                    if "matcher" in group:
                        re.compile(group["matcher"])
                    for handler in group["hooks"]:
                        if not isinstance(handler, dict):
                            raise ValueError("invalid hook handler")
                        if handler.get("type") not in {"command", "mcp_tool"}:
                            finding(relative, "hook-handler-not-executed-by-codex", "medium")
                        if handler.get("type") == "command":
                            command = handler.get("command")
                            if not isinstance(command, str) or not command.strip():
                                raise ValueError("missing hook command")
                            if re.search(r"\b(?:curl|wget)\b[^\n]*\|\s*(?:ba)?sh\b", command):
                                finding(relative, "hook-download-and-execute")
            inputs.append({"path": relative, "sha256": sha(path)})
        except (OSError, ValueError, TypeError, AttributeError, re.error):
            incomplete.append(relative)
    return {"status": "incomplete" if incomplete else "findings" if findings else "passed", "engine": "builtin-codex-config",
            "findings": findings, "unscanned": incomplete, "inputs": inputs,
            "note": "Limited configuration checks. Hook trust, live enforcement and prompt-injection detection are not established by this result."}


def snapshot_inputs(root, destination):
    candidates = ["AGENTS.md", ".codex/config.toml", ".codex/hooks.json"]
    candidates += [p.relative_to(root).as_posix() for p in sorted((root / ".agents/skills").glob("*/SKILL.md"))]
    candidates += [p.relative_to(root).as_posix() for p in sorted((root / ".agents/skills").glob("*/references/*.md"))]
    mapping, fingerprints, total = {}, {}, 0
    if len(candidates) > 1000:
        raise ValueError("AgentShield input count exceeds limit")
    for relative in candidates:
        if not (root / relative).exists():
            continue
        path = local_file(root, relative)
        size = path.stat().st_size
        total += size
        if size > 2 * 1024 * 1024 or total > 64 * 1024 * 1024:
            raise ValueError("AgentShield input exceeds size limit")
        parts = Path(relative).parts
        if relative.startswith(".agents/skills/"):
            # Native discovery omits nested .agents skills. Flatten copies only,
            # preserve contents and map every reported location to the source.
            mirror = f"skills/{parts[2]}.md" if parts[-1] == "SKILL.md" else f"rules/{parts[2]}--{parts[-1]}"
        else:
            mirror = relative
        target = destination / mirror
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())
        mapping[mirror] = relative
        fingerprints[relative] = sha(path)
    return mapping, fingerprints


def normalize(report, code, mapping, snapshot):
    if not isinstance(report, dict) or not isinstance(report.get("findings"), list) or not isinstance(report.get("summary"), dict):
        raise ValueError("unsupported AgentShield JSON report")
    summary = report["summary"]
    raw = report["findings"]
    if (type(summary.get("filesScanned")) is not int or type(summary.get("totalFindings")) is not int
            or summary["filesScanned"] != len(mapping) or summary["totalFindings"] != len(raw)):
        raise ValueError("AgentShield scan coverage or totals incomplete")
    findings = []
    levels = {"critical", "high", "medium", "low", "info"}
    for item in raw:
        if not isinstance(item, dict) or item.get("severity") not in levels or not re.fullmatch(r"[A-Za-z0-9_.:/-]{1,160}", str(item.get("id", ""))):
            raise ValueError("invalid AgentShield finding")
        name = item.get("file")
        if not isinstance(name, str):
            raise ValueError("missing AgentShield source location")
        if Path(name).is_absolute():
            name = Path(name).resolve().relative_to(snapshot.resolve()).as_posix()
        if name not in mapping:
            raise ValueError("AgentShield finding is outside declared inputs")
        finding = {"path": mapping[name], "rule": item["id"], "severity": item["severity"]}
        if "line" in item:
            if type(item["line"]) is not int or item["line"] < 1:
                raise ValueError("invalid AgentShield line")
            finding["line"] = item["line"]
        findings.append(finding)
    for level in levels:
        if type(summary.get(level)) is not int or summary[level] != sum(f["severity"] == level for f in findings):
            raise ValueError("inconsistent AgentShield severity totals")
    if code != (2 if any(f["severity"] == "critical" for f in findings) else 0):
        raise ValueError("AgentShield exit status disagrees with report")
    return {"status": "findings" if findings else "passed", "findings": findings, "scanned_count": len(mapping)}


def agentshield(root):
    base = {"engine": "agentshield", "expected_version": AGENTSHIELD_VERSION,
            "note": "Static CLI only; no fixes, model calls, hook execution or online supply-chain lookup."}
    package_path = root / AGENTSHIELD_PACKAGE
    if not package_path.is_file() or not shutil.which("node"):
        return {**base, "status": "unavailable", "reason": "pinned_agentshield_not_installed"}
    try:
        package = load(local_file(root, AGENTSHIELD_PACKAGE))
        if package.get("name") != "ecc-agentshield" or package.get("version") != AGENTSHIELD_VERSION:
            raise ValueError("AgentShield version mismatch")
        entry = local_file(root, str(Path(AGENTSHIELD_PACKAGE).parent / "dist/index.js"))
        with tempfile.TemporaryDirectory(prefix="agentshield-input-") as temporary:
            snapshot = Path(temporary)
            mapping, fingerprints = snapshot_inputs(root, snapshot)
            if not mapping:
                raise ValueError("no AgentShield inputs")
            executed = _execute([shutil.which("node"), str(entry), "scan", "--path", str(snapshot), "--format", "json"],
                                snapshot, _environment(snapshot), timeout=60)
            if executed.get("error"):
                return {**base, "status": "incomplete", "reason": executed["error"]}
            result = normalize(strict_json(executed["output"]), executed["exit_code"], mapping, snapshot)
        if any(sha(local_file(root, p)) != digest for p, digest in fingerprints.items()):
            result["status"] = "stale"
        return {**base, **result, "inputs": [{"path": p, "sha256": digest} for p, digest in fingerprints.items()]}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return {**base, "status": "incomplete", "reason": "invalid_incomplete_or_failed_agentshield_scan"}
