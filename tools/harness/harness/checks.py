"""Scope selection, exact command execution and local verification evidence."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import uuid
import xml.etree.ElementTree as ET

from .core import canonical_relative, changed_paths, files, fingerprint, git, inside, manifest, matches, runtime_path, strict_json, write_json
from .processes import execute
from . import provenance
from . import security_profiles


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(1024 * 1024):
            value.update(block)
    return value.hexdigest()


def intact(record: dict) -> bool:
    try:
        return all(Path(record[field]).is_file() and not Path(record[field]).is_symlink()
                   and record.get(field + '_sha256') == digest(Path(record[field]))
                   for field in ('log', 'test_report') if record.get(field)) and bool(record.get('log'))
    except (OSError, ValueError, TypeError):
        return False


def validate_result(record: dict, check: dict | None = None) -> None:
    """Recheck execution facts and raw summaries before trusting a pass label."""
    if (not isinstance(record, dict) or record.get('status') != 'passed'
            or type(record.get('exit_code')) is not int or record['exit_code'] != 0
            or record.get('execution_error') is not None or record.get('summary_error') is not None
            or record.get('failed_count') not in (None, 0)
            or not intact(record)):
        raise ValueError('invalid passing check result or missing/tampered artifacts')
    if check is not None and (record.get('check') != check['id']
            or record.get('covers_behavior') is not (check['id'] != 'doctor' and check.get('covers_behavior', True))):
        raise ValueError('cached result disagrees with registered check')
    summary = check.get('test_summary') if check is not None else record.get('test_summary')
    if summary is None and record.get('test_count') is not None:
        summary = 'junit' if record.get('test_report') else 'unittest'
    if summary not in (None, 'unittest', 'junit'):
        raise ValueError('unsupported result summary')
    log = Path(record['log'])
    maximum = (check or {}).get('max_output_bytes', 64 * 1024 * 1024) + 256
    if log.stat().st_size > maximum:
        raise ValueError('result log exceeds its output budget')
    if summary is None:
        return
    if summary == 'unittest':
        with log.open('rb') as stream:
            output = stream.read(maximum + 1)
        if len(output) > maximum:
            raise ValueError('result log exceeds its output budget')
        counts = unittest_counts(output.decode('utf-8', errors='replace'))
    else:
        counts = junit_counts(Path(record.get('test_report') or ''))
    if (not counts['test_count'] or counts['skipped_count'] + counts.get('expected_failure_count', 0) >= counts['test_count']
            or counts['failed_count']):
        raise ValueError('raw summary does not prove passing tests')
    for field in ('test_count', 'skipped_count', 'failed_count', 'expected_failure_count', 'flaky_count'):
        if type(record.get(field, 0)) is not int or record.get(field, 0) != counts.get(field, 0):
            raise ValueError('result counts disagree with raw summary: ' + field)
    if counts.get('flaky_count') and not (check or record).get('allow_flaky', False):
        raise ValueError('raw summary contains unaccepted flaky tests')


def reusable(record, check: dict) -> bool:
    try:
        validate_result(record, check)
        return True
    except (OSError, ValueError, KeyError, TypeError, AttributeError, ImportError, ET.ParseError):
        return False


def unittest_counts(output: str) -> dict:
    """Validate every runner summary, including contradictory exit-zero output."""
    summaries = list(re.finditer(r"^Ran (\d+) tests? in [0-9.eE+-]+s\s*$", output, re.M))
    if not summaries:
        raise ValueError("missing unittest execution summary")
    totals = dict(test_count=0, skipped_count=0, failed_count=0, expected_failure_count=0)
    for index, summary in enumerate(summaries):
        end = summaries[index + 1].start() if index + 1 < len(summaries) else len(output)
        tail = output[summary.end():end]
        verdicts = list(re.finditer(r"^(OK|FAILED|NO TESTS RAN)(?: \(([^\n]*)\))?\s*$", tail, re.M))
        if len(verdicts) != 1:
            raise ValueError("missing or contradictory unittest verdict")
        verdict = verdicts[0]
        counts = {}
        for field in (verdict[2] or "").split(","):
            if not field.strip():
                continue
            item = re.fullmatch(r"(skipped|expected failures|unexpected successes|failures|errors)=(\d+)", field.strip())
            if not item or item[1] in counts:
                raise ValueError("invalid unittest verdict counts")
            counts[item[1]] = int(item[2])
        executed = int(summary[1])
        if verdict[1] == "NO TESTS RAN" and executed != 0:
            raise ValueError("unittest empty verdict contradicts test count")
        failed = sum(counts.get(k, 0) for k in ("failures", "errors", "unexpected successes"))
        skipped, expected = counts.get("skipped", 0), counts.get("expected failures", 0)
        # A failed unittest method can contribute several failing subTests.
        # Such counts never establish a pass, but remain valid red evidence.
        if (skipped + expected > executed or failed > executed) and verdict[1] != 'FAILED':
            raise ValueError("unittest counts exceed executed tests")
        totals["test_count"] += executed
        totals["skipped_count"] += skipped
        totals["expected_failure_count"] += expected
        totals["failed_count"] += max(failed, int(verdict[1] == "FAILED"))
    # A custom runner may print OK after a genuine failure diagnostic.
    if re.search(r"^(?:(?:FAIL|ERROR|UNEXPECTED SUCCESS):|FAILED(?: \(|$))", output, re.M):
        totals["failed_count"] = max(totals["failed_count"], 1)
    return totals


def plan(root: Path, paths: list[str], full: bool = False, workflow: str | None = None, *, checkpoint='feature') -> dict:
    if checkpoint not in ('edit', 'feature', 'integration', 'final'):
        raise ValueError('invalid verification checkpoint')
    config = manifest(root, workflow)
    # Match the same canonical names that execution and provenance resolve.
    # Otherwise e.g. backend/other/../auth can evade backend/auth/** controls.
    paths = sorted({canonical_relative(root, path) for path in paths})
    docs = config.get("coverage", {}).get("documentation", [])
    reasons, deferred = {}, {}
    for check in config["checks"]:
        hits = [p for p in paths if matches(p, check["paths"])]
        if not full and checkpoint not in check.get('run_at', ['edit', 'feature', 'integration', 'final']):
            if (check.get('tier', 'change') == 'change' and hits) or (check.get('always', False) and any(not matches(p, docs) for p in paths)):
                deferred[check['id']] = check
            continue
        if full:
            reasons[check["id"]] = ["all registered checks requested"]
        elif check.get("tier", "change") == "change" and hits:
            reasons[check["id"]] = ["matching paths: " + ", ".join(hits)]
        if check.get("always", False) and any(not matches(p, docs) for p in paths):
            reasons.setdefault(check["id"], []).append("shared smoke check for behavioral changes")
    impact_checks = set()
    for impact in config.get("impacts", []):
        if any(matches(p, impact["paths"]) for p in paths):
            for name in impact["checks"]:
                reasons.setdefault(name, []).append(impact["reason"])
                impact_checks.add(name)
    review = config.get("security_review")
    registered = {c["id"]: c for c in config["checks"]}
    for control in review.get("controls", []) if review else []:
        affected = (config.get("workflow") in paths
                    or any(matches(p, control["paths"]) for p in paths))
        if full or affected:
            for name in control["checks"]:
                if full or checkpoint != "edit":
                    reasons.setdefault(name, []).append("required security control: " + control["area"])
                elif name not in reasons:
                    deferred[name] = registered[name]
    checks = [c for c in config["checks"] if c["id"] in reasons]
    deferred = {name: check for name, check in deferred.items() if name not in reasons}
    # Only a selected behavior check can cover a changed source; doctor and
    # a smoke check selected solely via `always` cannot hide missing coverage.
    behavior = [c for c in [*checks, *deferred.values()] if c["id"] != "doctor" and c.get("covers_behavior", True)]
    unknown = [p for p in paths if not matches(p, docs) and not any(matches(p, c["paths"]) for c in behavior)]
    if any(inside(root, p).is_file() for p in paths):
        inputs = {p.relative_to(root).as_posix() for p in files(root)}
        unknown = sorted(set(unknown) | {p for p in paths if inside(root, p).is_file() and p not in inputs})
    return {"checks": checks, "uncovered_paths": unknown, "paths": paths,
            "checkpoint": checkpoint, "deferred_checks": sorted(deferred),
            "selection_reasons": reasons, "workflow": config.get("workflow"),
            "configuration_pending": config.get("workflow_state") == "draft",
            "security_review": security_profiles.for_scope(review, paths, full=full, workflow=config.get("workflow"), impact_checks=impact_checks),
            "scope": "full_registered" if full else "selected"}


MAX_JUNIT_NODES = 250_000
MAX_JUNIT_DEPTH = 64


class _JUnitTree(ET.TreeBuilder):
    def __init__(self):
        super().__init__()
        self.depth = self.nodes = 0

    def start(self, tag, attrs):
        self.depth += 1
        self.nodes += 1
        if self.depth > MAX_JUNIT_DEPTH or self.nodes > MAX_JUNIT_NODES:
            raise ValueError('JUnit XML structure exceeds limits')
        return super().start(tag, attrs)

    def end(self, tag):
        result = super().end(tag)
        self.depth -= 1
        return result

    def doctype(self, name, pubid, system):
        raise ValueError('JUnit DTD/entities are unsupported')


def junit_counts(path: Path) -> dict:
    """Count actual testcases, not potentially duplicated nested suite totals."""
    if path.is_symlink():
        raise ValueError('fresh JUnit report cannot be a symlink')
    if not path.is_file():
        raise ValueError('JUnit report must be a regular file')
    with path.open('rb') as stream:
        content = stream.read(16 * 1024 * 1024 + 1)
    if len(content) > 16 * 1024 * 1024:
        raise ValueError('JUnit report exceeds 16 MiB limit')
    root = ET.fromstring(content, parser=ET.XMLParser(target=_JUnitTree()))
    local = lambda tag: tag.rsplit("}", 1)[-1]
    if local(root.tag) not in {"testsuite", "testsuites"}:
        raise ValueError("expected a JUnit testsuite or testsuites document")
    nodes = list(root.iter())
    cases = [node for node in nodes if local(node.tag) == "testcase"]
    skipped = sum(any(local(child.tag) == "skipped" for child in case) for case in cases)
    failed = sum(any(local(child.tag) in {"failure", "error"} for child in case) for case in cases)
    # Validate declared totals instead of letting negative values cancel errors
    # or a truncated report silently lose unexecuted/skipped tests.
    suite_errors = 0
    totals = {}
    for suite in reversed(nodes):
        is_case = local(suite.tag) == 'testcase'
        count = int(is_case) + sum(totals[child][0] for child in suite)
        skip_count = int(is_case and any(local(c.tag) == 'skipped' for c in suite)) + sum(totals[child][1] for child in suite)
        totals[suite] = count, skip_count
        if local(suite.tag) not in {"testsuite", "testsuites"}:
            continue
        declared = {}
        for field in ("tests", "errors", "failures", "skipped"):
            if field in suite.attrib:
                raw = suite.get(field)
                if not re.fullmatch(r"[0-9]+", raw):
                    raise ValueError("invalid nonnegative JUnit suite count")
                declared[field] = int(raw)
        if "tests" in declared and declared["tests"] != count:
            raise ValueError("JUnit declared test count disagrees with testcases")
        if "skipped" in declared and declared["skipped"] != skip_count:
            raise ValueError("JUnit declared skipped count disagrees with testcases")
        # Collection/setup errors can exist outside testcases and must fail.
        suite_errors = max(suite_errors, declared.get("errors", 0) + declared.get("failures", 0))
    flaky = sum(any(local(child.tag) in {"flakyFailure", "flakyError", "rerunFailure", "rerunError"}
                    for child in case) for case in cases)
    return {"test_count": len(cases), "skipped_count": skipped, "failed_count": max(failed, suite_errors),
            "flaky_count": flaky}


def run(root: Path, paths: list[str], *, full=False, reuse=False, report_dir: Path | None = None,
        workflow: str | None = None, checkpoint='feature') -> dict:
    before = fingerprint(root)
    selected = plan(root, paths, full, workflow, checkpoint=checkpoint)
    paths = selected["paths"]
    if selected["uncovered_paths"] or selected["configuration_pending"]:
        return {**selected, "status": "needs_configuration", "results": [],
                "note": "Register behavioral checks and include existing sources in provenance; ignored artifacts cannot silently serve as source inputs."}
    if not selected["checks"]:
        return {**selected, "status": "deferred" if selected['deferred_checks'] else "no_checks", "results": [], "product_accepted": False}
    source_snapshot = provenance.snapshot(root)
    source_executable = provenance.executable_snapshot(root)
    if fingerprint(root) != before:
        return {'status': 'stale', 'results': [], 'completion_ready': False, 'product_accepted': False,
                'note': 'Inputs changed during planning; no check commands were executed.'}
    base = report_dir or runtime_path(root, '.runtime/checks')
    run_id = uuid.uuid4().hex
    directory = base / run_id
    directory.mkdir(parents=True, exist_ok=False, mode=0o700)
    cache_path = runtime_path(root, '.runtime/check-cache.json')
    try:
        cache = provenance.load(cache_path)
        if not isinstance(cache, dict):
            cache = {}
    except (OSError, ValueError):
        cache = {}
    results = []
    for check in selected["checks"]:
        test_report = directory / f"{check['id']}.xml"
        command = [sys.executable if x == "{python}" else x.replace("{report}", str(test_report.resolve())) for x in check["command"]]
        key = before + ":" + json.dumps(check, sort_keys=True)
        previous = cache.get(key)
        if not isinstance(previous, dict):
            previous = None
        if reuse and check.get("cacheable", False) and reusable(previous, check):
            results.append({**previous, "reused": True})
            continue
        logfile = directory / f"{check['id']}.log"
        started = time.monotonic()
        status, code, count = "failed", None, None
        execution = execute(command, cwd=inside(root, check.get("cwd", ".")), log=logfile,
                            timeout=check.get("timeout", 120),
                            max_output_bytes=check.get("max_output_bytes", 4 * 1024 * 1024))
        code = execution['exit_code']
        output = logfile.read_text(encoding="utf-8", errors="replace")
        skipped_count, failed_count, expected_failure_count, summary_error = None, None, 0, None
        flaky_count = 0
        if check.get("test_summary") == "unittest":
            try:
                counts = unittest_counts(output)
                count, skipped_count, failed_count, expected_failure_count = (counts[k] for k in
                    ("test_count", "skipped_count", "failed_count", "expected_failure_count"))
            except ValueError as exc:
                summary_error = str(exc)
        if check.get("test_summary") == "junit":
            try:
                counts = junit_counts(test_report)
                count, skipped_count, failed_count = (counts[k] for k in ("test_count", "skipped_count", "failed_count"))
                flaky_count = counts['flaky_count']
            except (OSError, ValueError, ImportError, ET.ParseError) as exc:
                summary_error = f"missing or invalid fresh JUnit report: {exc}"
        if code == 0:
            status = "passed"
            if check.get("test_summary") in {"unittest", "junit"}:
                if not count or skipped_count + expected_failure_count >= count:
                    status = "no_tests_executed"
                if failed_count:
                    status = "failed"
                if summary_error:
                    status = "invalid_test_report"
                if flaky_count and not check.get('allow_flaky', False):
                    status = 'flaky'
        if execution['error']:
            status = execution['error']
        record = {"check": check["id"], "status": status, "exit_code": code, "test_count": count,
                  "covers_behavior": check["id"] != "doctor" and check.get("covers_behavior", True),
                  "test_summary": check.get('test_summary'), "allow_flaky": check.get('allow_flaky', False),
                  "skipped_count": skipped_count, "failed_count": failed_count,
                  "expected_failure_count": expected_failure_count,
                  "flaky_count": flaky_count, "execution_error": execution['error'],
                  "output_bytes": execution['output_bytes'], "retained_bytes": execution['retained_bytes'],
                  "summary_error": summary_error,
                  "test_report": str(test_report.resolve()) if test_report.exists() else None,
                  "command": command, "cwd": check.get("cwd", "."), "log": str(logfile.resolve()),
                  "duration_seconds": round(time.monotonic() - started, 3), "reused": False}
        record['log_sha256'] = digest(logfile)
        if test_report.is_file():
            record['test_report_sha256'] = digest(test_report)
        results.append(record)
        if status == "passed" and check.get("cacheable", False):
            cache[key] = record
    after = fingerprint(root)
    status = "passed" if all(r["status"] == "passed" for r in results) else "failed"
    if status == 'passed' and selected['deferred_checks']:
        status = 'checkpoint_passed'
    if status in {"passed", "checkpoint_passed"} and selected["security_review"]["applicable_pending"]:
        status = "checks_passed_security_pending"
    try:
        plan_changed = plan(root, paths, full, workflow, checkpoint=checkpoint) != selected
    except (OSError, ValueError):
        plan_changed = True
    if after != before or plan_changed:
        status = "stale"
    # Only the current unchanged snapshot is reusable; don't accumulate unlimited keys.
    provenance.atomic(cache_path, {k: v for k, v in cache.items() if k.startswith(before + ":")} if status != "stale" else {})
    report = {"run_id": run_id, "created_at": datetime.now(timezone.utc).isoformat(),
              "status": status, "fingerprint": before, "scope": selected["scope"],
              "source_snapshot": source_snapshot, "environment": provenance.environment(),
              "source_executable": source_executable,
              "workspace": str(root.resolve()),
              "paths": paths, "results": results, "product_accepted": False,
              "workflow": selected["workflow"], "selection_reasons": selected["selection_reasons"],
              "checkpoint": checkpoint, "deferred_checks": selected['deferred_checks'],
              "security_review": selected["security_review"],
              "completion_ready": status == "passed",
              "note": "Only selected registered checks were verified; evaluate task acceptance separately."}
    provenance.atomic(directory / "report.json", report)
    report["report"] = str((directory / "report.json").resolve())
    return report


def captured_run(command: list[str], cwd: Path, report_base: Path, *, timeout=600) -> dict:
    """Bound a captured runner and validate its report before following paths."""
    controller = report_base / ('controller-' + uuid.uuid4().hex) / 'runner.log'
    execution = execute(command, cwd=cwd, log=controller, timeout=timeout, max_output_bytes=4 * 1024 * 1024)
    invalid = {'status': 'invalid_snapshot_result', 'results': [], 'completion_ready': False,
               'product_accepted': False, 'snapshot_exit_code': execution['exit_code'],
               'note': 'Captured runner failed result validation; raw output is not echoed.'}
    if execution['error']:
        return {**invalid, 'execution_error': execution['error']}
    try:
        result = strict_json(controller.read_text(encoding='utf-8'))
        if not isinstance(result, dict):
            return invalid
        reference = result.get('report')
        if reference:
            report_path = Path(reference)
            if (not report_path.is_absolute() or report_path.is_symlink()
                    or not report_path.resolve().is_relative_to(report_base.resolve())):
                return invalid
            result = provenance.load(report_path)
            if not isinstance(result, dict):
                return invalid
            result['report'] = str(report_path.resolve())
        if (result.get('status') not in {'passed', 'failed', 'stale', 'checkpoint_passed',
                'checks_passed_security_pending', 'needs_configuration', 'no_checks', 'deferred'}
                or not isinstance(result.get('results'), list)
                or any(not isinstance(r, dict) for r in result['results'])):
            return invalid
        if result['status'] in {'passed', 'checkpoint_passed', 'checks_passed_security_pending'}:
            if not reference or not result['results'] or any(r.get('status') != 'passed' for r in result['results']):
                return invalid
            if (result.get('workspace') != str(cwd.resolve())
                    or result.get('source_snapshot') != provenance.snapshot(cwd)
                    or result.get('source_executable') != provenance.executable_snapshot(cwd)
                    or result.get('environment') != provenance.environment()):
                return invalid
            for record in result['results']:
                validate_result(record)
        if execution['exit_code'] != 0 and result['status'] in {'passed', 'checkpoint_passed'}:
            return invalid
        result['snapshot_exit_code'] = execution['exit_code']
        result['product_accepted'] = False
        return result
    except (OSError, ValueError, TypeError, ImportError, ET.ParseError):
        return invalid


def staged(root: Path, full=False, workflow: str | None = None, *, checkpoint='feature') -> dict:
    paths = changed_paths(root, staged=True)
    if not paths:
        return {"status": "no_staged_changes", "results": []}
    index_before = hashlib.sha256(git(root, "ls-files", "--stage", "-z").stdout).hexdigest()
    with tempfile.TemporaryDirectory(prefix="harness-index-") as directory:
        snapshot = Path(directory)
        exported = git(root, "checkout-index", "--all", f"--prefix={snapshot}{os.sep}")
        if exported.returncode:
            raise ValueError("cannot export Git index")
        entry = snapshot / "tools/harness/run.py"
        if not entry.is_file():
            raise ValueError("staged snapshot has no tools/harness/run.py; stage required harness files first")
        inventory = git(root, 'ls-files', '--cached', '-z')
        if inventory.returncode:
            raise ValueError('cannot enumerate staged source inventory')
        provenance.atomic(snapshot / '.runtime/source-inputs.json',
                          sorted({os.fsdecode(p) for p in inventory.stdout.split(b'\0') if p}))
        # Execute the staged runner and staged tests. Never link the worktree's
        # .env, node_modules or .venv into this snapshot.
        report_base = runtime_path(root, '.runtime/checks/staged-' + uuid.uuid4().hex)
        args = [sys.executable, str(entry), "check", "--report-dir", str(report_base), "--paths", *paths]
        if checkpoint != 'feature':
            args.extend(['--checkpoint', checkpoint])
        if full:
            args.append("--full")
        if workflow:
            inside(snapshot, workflow)
            args.extend(["--project", workflow])
        report = captured_run(args, snapshot, report_base)
        report["snapshot"] = "git_index"
        report["index_fingerprint"] = index_before
        index_after = hashlib.sha256(git(root, "ls-files", "--stage", "-z").stdout).hexdigest()
        if index_after != index_before:
            report["status"] = "stale"
        report['completion_ready'] = report.get('status') == 'passed'
        report["note"] = "Verified exported index; external dependencies must also be installed inside the snapshot when needed."
        if report.get("report"):
            write_json(Path(report["report"]), report)
        return report
