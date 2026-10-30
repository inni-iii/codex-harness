"""Bounded local diagnostics. No installs, fixes, shell commands or raw reports.

These checks do not evaluate application authorization or prove secret absence.
Dependency audits use isolated input snapshots and explicit network consent.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import threading
import time
from urllib.parse import urlsplit

from .core import inside, source_paths, strict_json as _json
from .processes import _stop as stop_process

MAX_FILE = 2 * 1024 * 1024
MAX_TOTAL = 64 * 1024 * 1024
MAX_OUTPUT = 2 * 1024 * 1024
MAX_FINDINGS = 1000
RULE_VERSION = 2
# Deliberately narrow heuristics. Never include a match or its digest in output.
PATTERNS = {
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----"),
    "github-token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,255}|github_pat_[A-Za-z0-9_]{60,255})\b"),
    "aws-access-id": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "assigned-secret": re.compile(
        r'''(?ix)(?<![\w.-])[\w.-]{0,128}?(?:api[_-]?key|client[_-]?secret|access[_-]?token|refresh[_-]?token|auth[_-]?token|password|passwd|secret[_-]?key|private[_-]?key|token|secret)(?:[_\.-][\w.-]{1,128})?["']?\s*[:=]\s*(?:["'](?P<quoted>[^"'\r\n]{8,})["']|(?P<bare>[A-Za-z0-9_+/=.!@%&*~:$-]{8,})(?=$|[\s,;}\]]))'''),
    "bearer-literal": re.compile(r'''(?i)\bBearer[ \t]+[A-Za-z0-9_./+=-]{16,512}(?=["'\s]|$)'''),
    "credential-url": re.compile(r'''(?i)\b(?:postgres(?:ql)?|mysql|mariadb|mongodb(?:\+srv)?|redis|amqp)s?://[^\s/:@]+:[^\s/@]+@'''),
    "openai-token": re.compile(r"\bsk-(?:proj|svcacct|admin)-[A-Za-z0-9_-]{40,256}\b"),
    "anthropic-token": re.compile(r"\bsk-ant-(?:api|admin)\d{2}-[A-Za-z0-9_-]{40,256}\b"),
    "gitlab-token": re.compile(r"\bglpat-[A-Za-z0-9_-]{20,128}\b"),
    "slack-token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,256}\b"),
}


def _candidate(pattern: re.Pattern, content: str) -> bool:
    for match in pattern.finditer(content):
        if "quoted" in pattern.groupindex:
            value = match.group("quoted") or match.group("bare")
            # Recognize explicit environment/template references, not arbitrary
            # values containing words such as example, test or synthetic.
            if re.fullmatch(r"\$\{[A-Za-z_][A-Za-z0-9_]*\}|\$[A-Za-z_][A-Za-z0-9_]*|<[A-Za-z_][A-Za-z0-9_ -]*>|YOUR_[A-Z_]+|REPLACE_WITH_[A-Z_]+", value):
                continue
        return True
    return False


def _file(root: Path, relative: str) -> Path:
    path = inside(root, relative)
    # Reject links even when they happen to point inside the repository.
    cursor = root / relative
    while cursor != root and cursor.is_relative_to(root):
        if cursor.is_symlink():
            raise ValueError("symlink input is unsupported")
        cursor = cursor.parent
    if not path.is_file():
        raise ValueError("input is not a regular file")
    return path


def _read(path: Path) -> bytes:
    # A file can grow after stat; bound the read itself as well.
    with path.open("rb") as stream:
        data = stream.read(MAX_FILE + 1)
    if len(data) > MAX_FILE:
        raise ValueError("input size limit")
    return data


def secrets(root: Path, paths: list[str] | None = None) -> dict:
    """Scan Git source snapshot (tracked + untracked), or explicit local files."""
    selected = sorted(set(source_paths(root) if paths is None else paths))
    findings, unscanned, scanned = [], [], []
    total = 0
    for relative in selected:
        if len(findings) >= MAX_FINDINGS:
            unscanned.append({"path": relative, "reason": "finding_limit"})
            continue
        # Deleted tracked files are not part of the current source snapshot.
        if not (root / relative).exists() and not (root / relative).is_symlink():
            if paths is not None:
                unscanned.append({"path": relative, "reason": "missing_input"})
            continue
        try:
            path = _file(root, relative)
            if path.stat().st_size > MAX_FILE:
                unscanned.append({"path": relative, "reason": "file_size_limit"})
                continue
            if total + path.stat().st_size > MAX_TOTAL:
                unscanned.append({"path": relative, "reason": "scan_size_limit"})
                continue
            data = _read(path)
            total += len(data)
            if len(data) > MAX_FILE or total > MAX_TOTAL:
                unscanned.append({"path": relative, "reason": "scan_size_limit"})
                continue
            if b"\0" in data:
                unscanned.append({"path": relative, "reason": "binary_input"})
                continue
            text = data.decode("utf-8")
            scanned.append({"path": relative, "sha256": hashlib.sha256(data).hexdigest()})
            limited = False
            for line, content in enumerate(text.splitlines(), 1):
                for rule, pattern in PATTERNS.items():
                    if _candidate(pattern, content):
                        findings.append({"path": relative, "line": line, "rule": rule})
                        if len(findings) >= MAX_FINDINGS:
                            limited = True
                            break
                if limited:
                    unscanned.append({"path": relative, "reason": "finding_limit"})
                    break
        except (OSError, UnicodeError, ValueError):
            # Exceptions may contain sensitive filenames/contents; return a code.
            unscanned.append({"path": relative, "reason": "unreadable_or_unsafe_input"})
    return {"status": "findings" if findings else "incomplete" if unscanned else "passed" if scanned else "no_inputs",
            "mode": "secrets", "rule_version": RULE_VERSION,
            "scope": "explicit_files" if paths is not None else "git_sources_or_source_archive",
            "scanned_count": len(scanned), "inputs": scanned, "findings": findings,
            "unscanned": unscanned, "created_at": datetime.now(timezone.utc).isoformat(),
            "note": "Limited text-pattern candidates only; ignored local files and Git history are not scanned by default. No finding does not prove secret absence."}


def _kill(process):
    try:
        return stop_process(process)
    except OSError:
        return "process_cleanup_failed"


def _execute(command: list[str], cwd: Path, env: dict, timeout: float = 45) -> dict:
    """Read bounded bytes; never persist or echo untrusted scanner output."""
    started = time.monotonic()
    try:
        process = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   start_new_session=os.name == "posix")
    except OSError:
        return {"error": "cannot_execute", "exit_code": None}
    output = bytearray()
    exceeded = threading.Event()
    cleanup_failed = threading.Event()
    cleanup_reason = []
    def stop():
        reason = _kill(process)
        if reason:
            cleanup_reason.append(reason)
            cleanup_failed.set()
    byte_count = 0
    lock = threading.Lock()
    def read(stream, retain):
        nonlocal byte_count
        try:
            while True:
                chunk = stream.read(65536)
                if not chunk:
                    break
                with lock:
                    byte_count += len(chunk)
                    if byte_count > MAX_OUTPUT:
                        exceeded.set()
                        stop()
                        break
                    if retain:
                        output.extend(chunk)
        except OSError:
            exceeded.set()
    readers = [threading.Thread(target=read, args=(process.stdout, True), daemon=True),
               threading.Thread(target=read, args=(process.stderr, False), daemon=True)]
    for reader in readers:
        reader.start()
    error = None
    try:
        process.wait(timeout=timeout)
        for reader in readers:
            reader.join(timeout=max(0.01, timeout - (time.monotonic() - started)))
        if any(reader.is_alive() for reader in readers):
            error = "output_stream_timeout"
            stop()
            for reader in readers:
                reader.join(timeout=1)
        if exceeded.is_set():
            error = "output_limit_or_read_error"
    except subprocess.TimeoutExpired:
        error = "timeout"
        stop()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            error = "process_cleanup_timeout"
        for reader in readers:
            reader.join(timeout=1)
    finally:
        stop()
        if not any(reader.is_alive() for reader in readers):
            process.stdout.close()
            process.stderr.close()
    if cleanup_failed.is_set():
        error = error or cleanup_reason[0]
    if error:
        return {"error": error, "exit_code": process.returncode,
                "cleanup_error": cleanup_reason[0] if cleanup_failed.is_set() else None}
    try:
        return {"output": output.decode("utf-8"), "exit_code": process.returncode}
    except UnicodeError:
        return {"error": "invalid_output_encoding", "exit_code": process.returncode}


def _environment(home: Path) -> dict:
    # No inherited tokens, PYTHONPATH, NODE_OPTIONS, npm/pip config or proxies.
    return {"PATH": os.environ.get("PATH", os.defpath), "HOME": str(home),
            "TMPDIR": str(home), "TEMP": str(home), "TMP": str(home),
            "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "NO_COLOR": "1",
            "PYTHONNOUSERSITE": "1", "PIP_CONFIG_FILE": os.devnull,
            "PIP_DISABLE_PIP_VERSION_CHECK": "1"}


def _integer(value):
    return type(value) is int and value >= 0


def _npm_result(output: str, code: int, minimum_count: int) -> dict:
    data = _json(output)
    if isinstance(data, dict) and data.get("error"):
        # npm versions vary in whether the code has a dedicated field.
        codes = re.findall(r"\b(?:ENOTFOUND|EAI_AGAIN|ECONNREFUSED|ECONNRESET|ENETUNREACH|ETIMEDOUT)\b", output)
        if codes:
            return {"status": "error", "reason": "registry_lookup_failed", "error_code": codes[0]}
    if not isinstance(data, dict) or data.get("auditReportVersion") != 2 or "error" in data:
        raise ValueError("unsupported audit result")
    vulns = data["vulnerabilities"]
    counts = data["metadata"]["vulnerabilities"]
    count = data["metadata"]["dependencies"]["total"]
    levels = ("info", "low", "moderate", "high", "critical")
    if (not isinstance(vulns, dict) or not all(_integer(counts[k]) for k in (*levels, "total"))
            or not _integer(count) or count < minimum_count or count == 0
            or counts["total"] != sum(counts[k] for k in levels) or counts["total"] != len(vulns)):
        raise ValueError("incomplete audit result")
    findings = []
    for name, issue in vulns.items():
        if not re.fullmatch(r"(?:@[a-z0-9._-]+/)?[a-z0-9._-]{1,214}", name) or issue["severity"] not in levels:
            raise ValueError("invalid vulnerability")
        advisory_ids = []
        for via in issue.get("via", []):
            if isinstance(via, dict):
                # Keep only a GitHub advisory identifier, not arbitrary URLs/text.
                match = re.fullmatch(r"https://github\.com/advisories/(GHSA-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4})", str(via.get("url", "")))
                if match:
                    advisory_ids.append(match[1])
        findings.append({"package": name, "severity": issue["severity"], "advisories": sorted(set(advisory_ids))})
    if any(counts[level] != sum(f["severity"] == level for f in findings) for level in levels):
        raise ValueError("inconsistent severity counts")
    if code != (1 if findings else 0):
        raise ValueError("exit code disagrees with report")
    return {"status": "findings" if findings else "passed", "audited_count": count, "findings": findings}


def _pip_result(output: str, code: int, expected: dict) -> dict:
    data = _json(output)
    if not isinstance(data, dict) or not isinstance(data.get("dependencies"), list) or data.get("fixes"):
        raise ValueError("unsupported audit result")
    observed, findings = {}, []
    for dependency in data["dependencies"]:
        name, version, vulns = dependency["name"], dependency["version"], dependency["vulns"]
        name = re.sub(r"[-_.]+", "-", name).lower()
        if dependency.get("skip_reason") or name in observed or expected.get(name) != version or not isinstance(vulns, list):
            raise ValueError("skipped or unexpected dependency")
        observed[name] = version
        for issue in vulns:
            advisory = issue["id"]
            if not isinstance(advisory, str) or not re.fullmatch(r"[A-Za-z0-9-]{1,80}", advisory):
                raise ValueError("invalid advisory")
            findings.append({"package": name, "version": version, "advisory": advisory})
    if observed != expected or not observed or code != (1 if findings else 0):
        raise ValueError("incomplete audit result or exit code disagreement")
    return {"status": "findings" if findings else "passed", "audited_count": len(observed), "findings": findings}


def _requirements(content: str) -> dict:
    expected = {}
    for line in content.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.fullmatch(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)==([0-9][A-Za-z0-9.!+_-]*)\s*", line)
        if not match:
            raise ValueError("requires flattened exact pins")
        name = re.sub(r"[-_.]+", "-", match[1]).lower()
        if name in expected:
            raise ValueError("duplicate requirement")
        expected[name] = match[2]
    if not expected:
        raise ValueError("no requirements")
    return expected


def _npm_inputs(root: Path, relative: str) -> tuple[bytes, bytes, int]:
    lock_path = _file(root, relative)
    if lock_path.name != "package-lock.json" or lock_path.stat().st_size > MAX_FILE:
        raise ValueError("unsupported npm lock")
    package_path = _file(root, (Path(relative).parent / "package.json").as_posix())
    if package_path.stat().st_size > MAX_FILE:
        raise ValueError("oversized manifest")
    lock_bytes, package_bytes = _read(lock_path), _read(package_path)
    lock, package = _json(lock_bytes.decode()), _json(package_bytes.decode())
    if lock.get("lockfileVersion") not in (2, 3) or not isinstance(lock.get("packages"), dict) or not isinstance(package, dict):
        raise ValueError("unsupported lock format")
    packages = lock["packages"]
    if "" not in packages or len(packages) < 2 or package.get("workspaces"):
        raise ValueError("empty or workspace lock unsupported")
    for group in ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies"):
        if packages[""].get(group, {}) != package.get(group, {}):
            raise ValueError("manifest and lock disagree")
        if any(not isinstance(spec, str) or re.match(r"(?:file:|link:|git|https?:|npm:)", spec)
               for spec in package.get(group, {}).values()):
            raise ValueError("non-registry dependency")
    for name, info in packages.items():
        if not name:
            continue
        part = r"node_modules/(?:@[a-z0-9._-]+/)?[a-z0-9._-]+"
        if not re.fullmatch(part + r"(?:/" + part + r")*", name) or any(p in (".", "..") for p in name.split("/")):
            raise ValueError("unsafe package path")
        parsed = urlsplit(info.get("resolved", ""))
        if (info.get("link") or not isinstance(info.get("version"), str)
                or not re.fullmatch(r"sha512-[A-Za-z0-9+/]{86}==", str(info.get("integrity", "")))
                or parsed.scheme != "https" or parsed.netloc != "registry.npmjs.org"
                or parsed.username or parsed.password):
            raise ValueError("only integrity-locked public npm registry packages supported")
    return lock_bytes, package_bytes, len(packages) - 1


def dependencies(root: Path, *, npm_locks: list[str], requirements: list[str], allow_network=False) -> dict:
    targets = [("npm", p) for p in npm_locks] + [("pip-audit", p) for p in requirements]
    base = {"mode": "dependencies", "created_at": datetime.now(timezone.utc).isoformat(),
            "results": [], "note": "Known-advisory lookup of explicit snapshots; no installation, fixes or malicious-package detection. Package names/versions leave this machine only with --allow-network."}
    if not targets:
        return {**base, "status": "needs_configuration", "reason": "explicit_dependency_input_required"}
    if not allow_network:
        return {**base, "status": "network_not_authorized"}
    for tool, relative in targets:
        record = {"tool": tool, "input": relative, "status": "needs_configuration"}
        base["results"].append(record)
        try:
            path = _file(root, relative)
            if path.stat().st_size > MAX_FILE:
                raise ValueError("oversized input")
            if tool == "npm":
                lock, package, expected = _npm_inputs(root, relative)
                raw = lock  # Hash exactly the snapshot sent to the scanner.
            else:
                raw = _read(path)
                expected = _requirements(raw.decode("utf-8"))
            record["sha256"] = hashlib.sha256(raw).hexdigest()
            executable = shutil.which(tool)
            if not executable:
                record.update(status="unavailable", reason="scanner_not_installed")
                continue
            # OS temp has private permissions; no .npmrc, sitecustomize or
            # source imports from the target repository are copied here.
            with tempfile.TemporaryDirectory(prefix="harness-security-") as tmp:
                isolated = Path(tmp)
                env = _environment(isolated)
                version = _execute([executable, "--version"], isolated, env, timeout=10)
                if (version.get("error") or version["exit_code"] != 0
                        or not re.fullmatch(r"(?:pip-audit\s+)?[0-9]+\.[0-9]+\.[0-9]+(?:[A-Za-z0-9.+-]*)\s*", version.get("output", ""))):
                    record.update(status="error", reason="invalid_scanner_version")
                    continue
                record["version"] = version["output"].strip()
                if tool == "npm":
                    (isolated / "package-lock.json").write_bytes(lock)
                    (isolated / "package.json").write_bytes(package)
                    record["manifest_sha256"] = hashlib.sha256(package).hexdigest()
                    for name in ("user.npmrc", "global.npmrc"):
                        (isolated / name).touch()
                    command = [executable, "audit", "--json", "--package-lock-only", "--ignore-scripts",
                               "--audit-level=info", "--include=dev", "--include=optional", "--include=peer",
                               "--registry=https://registry.npmjs.org", "--fetch-retries=0", "--fetch-timeout=15000",
                               "--userconfig=" + str(isolated / "user.npmrc"),
                               "--globalconfig=" + str(isolated / "global.npmrc"), "--cache=" + str(isolated / "cache")]
                else:
                    (isolated / "requirements.txt").write_text("".join(f"{n}=={v}\n" for n, v in expected.items()))
                    command = [executable, "-r", "requirements.txt", "--no-deps", "--disable-pip", "--format=json",
                               "--progress-spinner=off", "--vulnerability-service=pypi", "--timeout=15"]
                executed = _execute(command, isolated, env)
                record["exit_code"] = executed["exit_code"]
                if executed.get("error"):
                    record.update(status="error", reason=executed["error"])
                    if executed.get("cleanup_error"):
                        record["cleanup_error"] = executed["cleanup_error"]
                    continue
                try:
                    record.update(_npm_result(executed["output"], executed["exit_code"], expected) if tool == "npm"
                                  else _pip_result(executed["output"], executed["exit_code"], expected))
                except (ValueError, KeyError, TypeError, AttributeError, RecursionError):
                    record.update(status="error", reason="invalid_incomplete_or_failed_scanner_result")
            # A modified source snapshot cannot borrow the old audit result.
            if _read(path) != raw or (tool == "npm" and _read(path.with_name("package.json")) != package):
                record.update(status="stale", reason="input_changed_during_audit")
        except (ValueError, OSError, UnicodeError, KeyError, TypeError, AttributeError, RecursionError):
            record.update(status="needs_configuration", reason="unsupported_or_unsafe_dependency_input")
    statuses = {r["status"] for r in base["results"]}
    return {**base, "status": "passed" if statuses == {"passed"} else "findings" if statuses <= {"passed", "findings"} else "incomplete"}
