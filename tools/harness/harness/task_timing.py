"""Explicit local phase marks; no guessed thinking time or hidden telemetry."""
from __future__ import annotations

from datetime import datetime
import math
from pathlib import Path
import re

from . import evidence, provenance as p
from .core import inside


def stamp(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(value)
    except (ValueError, TypeError):
        raise ValueError('timing requires valid timezone-aware timestamps') from None
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError('timing requires timezone-aware timestamps')
    return result


def state(root: Path, slug: str, now: str):
    task = p.load(evidence.task_file(root, slug))
    relative = f'.runtime/task-timing/{slug}.json'
    path = inside(root, relative)
    cursor = root
    for part in Path(relative).parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError('symlink timing paths are unsupported')
    start = task['created_at']
    end = task.get('completed_at') if task.get('status') == 'complete' else now
    if stamp(end) < stamp(start) or stamp(end) > stamp(now):
        raise ValueError('task clock is outside the observed time range')
    before = p.sha(path) if path.exists() else None
    ledger = p.load(p.local_file(root, relative)) if path.exists() else {
        'version': 1, 'task': slug, 'created_at': start, 'marks': []}
    if (not isinstance(ledger, dict) or ledger.get('version') != 1 or ledger.get('task') != slug
            or ledger.get('created_at') != start or not isinstance(ledger.get('marks'), list)):
        raise ValueError('timing ledger differs from this task')
    last = stamp(start)
    for mark in ledger['marks']:
        if (not isinstance(mark, dict) or set(mark) != {'phase', 'at'}
                or not isinstance(mark['phase'], str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,63}', mark['phase'])):
            raise ValueError('invalid timing phase record')
        current = stamp(mark['at'])
        if not last <= current <= stamp(end):
            raise ValueError('timing marks must be ordered within the task lifetime')
        last = current
    return task, path, ledger, end, before


def mark(root: Path, slug: str, phase: str) -> dict:
    root = root.resolve()
    if not re.fullmatch(r'[a-z][a-z0-9-]{0,63}', phase):
        raise ValueError('phase needs a short lowercase identifier')
    now = p.now()
    task, path, ledger, _, before = state(root, slug, now)
    if task.get('status') == 'complete':
        raise ValueError('cannot mark a completed task')
    if ledger['marks'] and ledger['marks'][-1]['phase'] == phase:
        return {'status': 'unchanged', 'task': slug, 'phase': phase}
    ledger['marks'].append({'phase': phase, 'at': now})
    if (p.sha(path) if path.exists() else None) != before:
        raise ValueError('timing ledger changed; reassess the newer record')
    p.atomic(path, ledger)
    return {'status': 'recorded', 'task': slug, 'phase': phase, 'at': now}


def report(root: Path, slug: str) -> dict:
    root = root.resolve()
    task, _, ledger, end, _ = state(root, slug, p.now())
    totals = {}
    phase, start = 'unclassified', stamp(task['created_at'])
    for item in ledger['marks'] + [{'phase': 'end', 'at': end}]:
        current = stamp(item['at'])
        totals[phase] = totals.get(phase, 0) + (current - start).total_seconds()
        phase, start = item['phase'], current
    runs, seen = [], set()
    task_path = evidence.task_file(root, slug)
    for entry in task['evidence'].values():
        if entry['type'] != 'check':
            continue
        evidence.verify_entry(root, entry, task_path, require_current=False)
        key = (entry['path'], entry['sha256'])
        if key in seen:
            continue
        seen.add(key)
        saved = p.load(p.local_file(root, entry['path']))
        durations = [row.get('duration_seconds') for row in saved['results']]
        if any(type(n) not in (int, float) or not math.isfinite(n) or n < 0 for n in durations):
            raise ValueError('check report has no usable execution durations')
        runs.append({'path': entry['path'], 'execution_seconds': round(sum(durations), 3),
                     'reused_checks': sum(row.get('reused') is True for row in saved['results'])})
    return {'status': 'observed', 'task': slug, 'start': task['created_at'], 'end': end,
            'wall_seconds': round((stamp(end) - stamp(task['created_at'])).total_seconds(), 3),
            'phase_seconds': {k: round(v, 3) for k, v in totals.items()}, 'check_runs': runs,
            'recorded_check_seconds': round(sum(r['execution_seconds'] for r in runs), 3),
            'note': 'Phase wall time is explicit, not inferred activity/CPU time. Unmarked time is unclassified. '
                    'Checks overlap phases; reused-check durations describe original runs, not new work. '
                    'Only registered check evidence is included; content integrity is checked, source currency is not.'}
