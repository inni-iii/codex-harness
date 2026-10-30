"""Recorded review rounds and regression obligations; no autonomous agent loop."""
from __future__ import annotations

from pathlib import Path
import re
import xml.etree.ElementTree as ET

from . import checks, provenance as p

AREAS = {
    'research': ['question_coverage', 'source_conditions', 'counterevidence', 'claim_limits'],
    'experiment': ['protocol', 'input_conditions', 'measurement', 'aggregation'],
    'design': ['contracts', 'quality_scenarios', 'alternatives', 'verification_plan'],
    'implement': ['requirements', 'failure_paths', 'shared_boundaries', 'regressions'],
    'debug': ['reproduction', 'cause', 'fix_scope', 'regressions'],
    'review': ['requirements', 'defects', 'shared_boundaries', 'evidence'],
}


def template(kind: str) -> dict:
    return {'scope': '', 'areas': [{'name': name, 'result': 'pending', 'reason': ''} for name in AREAS[kind]],
            'findings': [], 'rounds': [{'id': 'R1', 'new_findings': [], 'closed_findings': [],
                                       'outcome': 'pending', 'reason': '', 'evidence': []}]}


def text(value, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError('verification requires ' + label)


def references(values, entries: dict) -> None:
    if (not isinstance(values, list) or not values or not all(isinstance(x, str) and x in entries for x in values)
            or len(set(values)) != len(values)):
        raise ValueError('verification needs distinct, registered evidence IDs')


def observed_case(record: dict, ident: str, *, failed: bool) -> bool:
    if record.get('test_summary') == 'unittest':
        with Path(record['log']).open('rb') as stream:
            raw = stream.read(64 * 1024 * 1024 + 1)
        if len(raw) > 64 * 1024 * 1024:
            raise ValueError('regression log exceeds limit')
        identity = re.compile(r'(?<!\w)' + re.escape(ident) + r'(?!\w)')
        lines = raw.decode('utf-8', errors='replace').splitlines()
        outcomes = []
        for index, line in enumerate(lines):
            if not identity.search(line):
                continue
            candidate = line
            if ' ... ' not in line and line.rstrip().endswith(')') and index + 1 < len(lines):
                following = lines[index + 1]
                if not re.match(r'^\S+ \([^\n]+\)', following):
                    candidate = following  # unittest shortDescription appears on the next line.
            if ' ... ' in candidate:
                outcomes.append(candidate.rsplit(' ... ', 1)[1].strip())
        return bool(outcomes) and (any(x in ('FAIL', 'ERROR') for x in outcomes) if failed else all(x == 'ok' for x in outcomes))
    if record.get('test_summary') == 'junit':
        path = Path(record.get('test_report') or '')
        checks.junit_counts(path)  # Recheck size/shape before inspecting case identities.
        matched = []
        for node in ET.parse(path).iter():
            if node.tag.rsplit('}', 1)[-1] != 'testcase':
                continue
            name, cls = node.get('name', ''), node.get('classname', '')
            if ident not in {name, cls + '.' + name}:
                continue
            children = {c.tag.rsplit('}', 1)[-1] for c in node}
            bad = bool(children & {'failure', 'error'})
            clean = not children.intersection({'failure', 'error', 'skipped', 'flakyFailure', 'flakyError', 'rerunFailure', 'rerunError'})
            matched.append(bad if failed else clean)
        return bool(matched) and (any(matched) if failed else all(matched))
    return False


def automated_regression(root: Path, case: dict, entries: dict, *, require_current: bool,
                         allow_missing_runtime: bool) -> None:
    for key in ('test_path', 'test_id', 'sha256', 'check', 'before', 'after'):
        text(case.get(key), 'automated regression ' + key)
    if case['before'] == case['after'] or any(key not in entries for key in (case['before'], case['after'])):
        raise ValueError('regression needs separate registered before/after evidence')
    before, after = entries[case['before']], entries[case['after']]
    if before['type'] != 'artifact' or after['type'] != 'check' or after.get('check') != case['check']:
        raise ValueError('automated regression needs a failed report artifact and a passing behavior check')
    if require_current and p.sha(p.local_file(root, case['test_path'])) != case['sha256']:
        raise ValueError('regression test changed after verification')
    if allow_missing_runtime and any(e['path'].startswith('.runtime/') and not (root / e['path']).is_file()
                                     for e in (before, after)):
        return  # Doctor separately reports unavailable historical local evidence.
    red, green = [p.load(p.local_file(root, entry['path'])) for entry in (before, after)]
    if red.get('status') != 'failed' or green.get('status') != 'passed':
        raise ValueError('regression needs an observed failure followed by a passing run')
    if any(report.get('source_snapshot', {}).get(case['test_path']) != case['sha256'] for report in (red, green)):
        raise ValueError('the same unchanged regression test must exist in before/after inputs')
    failed = next((r for r in red.get('results', []) if r.get('check') == case['check']), None)
    if (failed is None or not checks.intact(failed) or failed.get('execution_error') is not None
            or failed.get('summary_error') is not None):
        raise ValueError('regression failure is missing, tampered or an execution/report error')
    summary = failed.get('test_summary')
    if summary == 'unittest':
        with Path(failed['log']).open('rb') as stream:
            raw = stream.read(64 * 1024 * 1024 + 1)
        if len(raw) > 64 * 1024 * 1024:
            raise ValueError('regression reproduction log exceeds limit')
        counts = checks.unittest_counts(raw.decode('utf-8', errors='replace'))
    elif summary == 'junit':
        counts = checks.junit_counts(Path(failed.get('test_report') or ''))
    else:
        raise ValueError('automated reproduction needs a parsed test failure; document other reproductions as manual')
    if counts['test_count'] <= 0 or counts['failed_count'] <= 0:
        raise ValueError('before evidence contains no actual failed test')
    passed = next((r for r in green.get('results', []) if r.get('check') == case['check']), None)
    if passed is None or not observed_case(failed, case['test_id'], failed=True) or not observed_case(passed, case['test_id'], failed=False):
        raise ValueError('regression case must be identified as failed before and passed after; use verbose unittest or named JUnit')


def validate(root: Path, task: dict, audit: dict, *, require_current=True, allow_missing_runtime=False) -> None:
    """Validate recorded obligations; reviewers remain responsible for meaning."""
    try:
        _validate(root, task, audit, require_current=require_current, allow_missing_runtime=allow_missing_runtime)
    except (KeyError, TypeError, AttributeError, StopIteration):
        raise ValueError('invalid verification rounds/findings structure') from None


def _validate(root: Path, task: dict, audit: dict, *, require_current, allow_missing_runtime) -> None:
    if not isinstance(audit, dict):
        raise ValueError('review requires verification scope, areas, rounds and findings')
    text(audit.get('scope'), 'review scope')
    areas = audit.get('areas')
    expected = AREAS[task['kind']]
    if not isinstance(areas, list) or len(areas) != len(expected) or {r['name'] for r in areas} != set(expected):
        raise ValueError('review must assess every applicable work-type area exactly once')
    for area in areas:
        if area.get('result') not in ('checked', 'not_applicable'):
            raise ValueError('verification area remains pending')
        text(area.get('reason'), 'area observation or applicability reason')
    entries = task['evidence']
    findings = audit.get('findings')
    if not isinstance(findings, list):
        raise ValueError('confirmed findings must be recorded explicitly, including an empty list when none were found')
    known = {}
    for finding in findings:
        ident = finding.get('id')
        text(ident, 'finding ID')
        if ident in known:
            raise ValueError('duplicate finding ID')
        known[ident] = finding
        text(finding.get('summary'), 'finding symptom')
        text(finding.get('cause'), 'finding cause or disposition reason')
        if finding.get('status') == 'out_of_scope':
            references([finding.get('follow_up')], entries)
            if entries[finding['follow_up']]['type'] != 'artifact':
                raise ValueError('out-of-scope defect needs a persistent follow-up artifact')
            continue
        if finding.get('status') != 'fixed':
            raise ValueError('unresolved confirmed finding prevents completion: ' + ident)
        case = finding.get('regression')
        if not isinstance(case, dict):
            raise ValueError('every fixed finding requires regression evidence: ' + ident)
        if case.get('mode') == 'automated':
            automated_regression(root, case, entries, require_current=require_current,
                                 allow_missing_runtime=allow_missing_runtime)
        elif case.get('mode') == 'manual':
            for field in ('why_not_automated', 'expected'):
                text(case.get(field), 'manual regression ' + field)
            if case.get('before') == case.get('after'):
                raise ValueError('manual regression needs distinct before/after observations')
            references(list(dict.fromkeys([case.get('case'), case.get('before'), case.get('after')])), entries)
            if entries[case['case']]['type'] != 'artifact':
                raise ValueError('manual regression scenario must be a recorded artifact')
            if any(entries[case[k]]['type'] not in ('artifact', 'source') for k in ('case', 'before', 'after')):
                raise ValueError('manual regression requires recorded scenario and before/after observations')
        else:
            raise ValueError('fixed finding needs automated or explicitly justified manual regression')
    if set(known) != set(task.get('findings', [])):
        raise ValueError('review must retain exactly the confirmed finding IDs registered in task.json')
    rounds = audit.get('rounds')
    if not isinstance(rounds, list) or not rounds:
        raise ValueError('record at least one actual review round')
    seen, closed, round_ids = set(), set(), set()
    for row in rounds:
        text(row.get('id'), 'review round ID')
        text(row.get('reason'), 'review round observation')
        if row['id'] in round_ids or row.get('outcome') not in ('new_findings', 'no_new_findings'):
            raise ValueError('invalid or unfinished review round')
        round_ids.add(row['id'])
        references(row.get('evidence'), entries)
        new, resolved = row.get('new_findings'), row.get('closed_findings')
        if (not isinstance(new, list) or not isinstance(resolved, list)
                or not all(isinstance(x, str) and x in known for x in [*new, *resolved])
                or len(set(new)) != len(new) or len(set(resolved)) != len(resolved)
                or seen.intersection(new) or closed.intersection(resolved)):
            raise ValueError('review round has unknown or duplicate findings')
        seen.update(new)
        if not set(resolved).issubset(seen):
            raise ValueError('finding cannot be closed before it was recorded')
        closed.update(resolved)
        if bool(new) != (row['outcome'] == 'new_findings'):
            raise ValueError('review round conclusion contradicts its new findings')
    if set(known) != seen or seen != closed or rounds[-1]['outcome'] != 'no_new_findings':
        raise ValueError('close all recorded findings and re-review the final result without new findings')
