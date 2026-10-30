"""Task closure validates linked records; reviewers still judge their meaning."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re

from . import provenance as p
from .core import inside

TYPES = {'artifact', 'source', 'check', 'experiment'}
REQUIRED = {'research': {'source', 'artifact'}, 'experiment': {'experiment', 'artifact'},
            'design': {'artifact'}, 'implement': {'check'}, 'debug': {'check'}, 'review': {'artifact'}}


def task_file(root: Path, slug: str) -> Path:
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', slug):
        raise ValueError('invalid task slug')
    return p.local_file(root, f'docs/tasks/{slug}/task.json')


def save_unchanged(path: Path, data: dict, expected: str) -> None:
    """Optimistic edit detection; independent work still needs one writer/worktree."""
    if p.sha(path) != expected:
        raise ValueError('task changed during verification; preserve the newer record and reassess')
    p.atomic(path, data)


def contract(data: dict) -> str:
    value = {key: data.get(key) for key in ('kind', 'goal', 'scope', 'constraints', 'inputs', 'depends_on')}
    if 'findings' in data:
        value['findings'] = data['findings']
    value['acceptance'] = [{k: c.get(k) for k in ('id', 'condition', 'method')} for c in data['acceptance']]
    return p.signature(value)


def bookkeeping(relative: str, task_path: Path, root: Path) -> bool:
    folder = task_path.parent.resolve().relative_to(root.resolve()).as_posix()
    return relative in {f'{folder}/task.json', f'{folder}/notes.md', f'{folder}/review.json'}


def current_sources(root: Path, report: dict, task_path: Path) -> None:
    if report.get('workspace') != str(root.resolve()):
        if report.get('snapshot') != 'working_tree' or report.get('snapshot_origin') != str(root.resolve()):
            raise ValueError('evidence was executed in a different workspace')
        snapshot_dir = Path(report.get('snapshot_directory', '')).resolve()
        if (not snapshot_dir.is_relative_to((root / '.runtime/check-snapshots').resolve())
                or report.get('workspace') != str(snapshot_dir)):
            raise ValueError('snapshot evidence has an invalid workspace origin')
    recorded = report.get('source_snapshot')
    if not isinstance(recorded, dict) or not recorded:
        raise ValueError('report has no source snapshot; rerun with the current harness')
    trim = lambda mapping: {k: v for k, v in mapping.items() if not bookkeeping(k, task_path, root)}
    if trim(recorded) != trim(p.snapshot(root)):
        raise ValueError('evidence source snapshot is stale')
    if report.get('source_executable') is None:
        raise ValueError('report has no executable metadata; rerun with the current harness')
    if trim(report['source_executable']) != trim(p.executable_snapshot(root)):
        raise ValueError('evidence source executable permissions changed')
    if report.get('environment') != p.environment():
        raise ValueError('evidence execution environment changed')


def verify_entry(root: Path, entry: dict, task_path: Path, *, require_current=True) -> None:
    if entry.get('type') not in TYPES or not isinstance(entry.get('description'), str) or not entry['description'].strip():
        raise ValueError('evidence needs a supported type and description')
    path = p.local_file(root, entry['path'])
    if p.sha(path) != entry.get('sha256'):
        raise ValueError('evidence content changed: ' + entry['path'])
    if bookkeeping(entry['path'], task_path, root):
        raise ValueError('task bookkeeping cannot serve as its own result evidence')
    if entry['type'] == 'source':
        if (not isinstance(entry.get('origin'), str) or not re.fullmatch(r'https?://[^\s/]+(?:/[^\s]*)?', entry['origin'])
                or not isinstance(entry.get('accessed_at'), str)):
            raise ValueError('source evidence needs its original URL and access date')
        datetime.fromisoformat(entry['accessed_at'])
    if entry['type'] == 'check':
        report = p.load(path)
        if report.get('status') != 'passed' or report.get('deferred_checks') or not report.get('results'):
            raise ValueError('check evidence requires a passing report with no deferred checks')
        if report.get('security_review', {}).get('applicable_pending'):
            raise ValueError('unfinished applicable security review prevents task closure')
        if require_current:
            current_sources(root, report, task_path)
        from .checks import validate_result
        for record in report['results']:
            validate_result(record)
        # Each acceptance condition must identify the actual behavior check.
        selected = next((r for r in report['results'] if r['check'] == entry.get('check')), None)
        if (selected is None or selected['check'] in {'doctor', 'secret-patterns'}
                or selected.get('covers_behavior') is not True):
            raise ValueError('evidence must name a behavior check, not configuration/pattern checks')
        if report.get('checkpoint') == 'edit':
            raise ValueError('edit checkpoint alone cannot close a task')
    if entry['type'] == 'experiment':
        from .experiments import verify_report
        verify_report(root, p.load(path), task_path=task_path, require_current=require_current)


def add(root: Path, slug: str, ident: str, kind: str, relative: str, criterion: str,
        method: str, description: str, *, check=None, origin=None, accessed_at=None) -> dict:
    root = root.resolve()
    path = task_file(root, slug)
    task_digest = p.sha(path)
    data = p.load(path)
    if not isinstance(data, dict):
        raise ValueError('task must be an object')
    if data.get('version') != 2 or data.get('status') == 'complete':
        raise ValueError('evidence edits require an open version-2 task')
    from .tasks import validate
    errors = validate(data, root=root, task_path=path)
    if errors:
        raise ValueError('invalid task record: ' + '; '.join(errors))
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*', ident) or ident in data['evidence']:
        raise ValueError('evidence ID must be new and simple')
    condition = next((c for c in data['acceptance'] if c['id'] == criterion), None)
    if condition is None or not method.strip():
        raise ValueError('specify an existing acceptance ID and a concrete verification method')
    entry = {'type': kind, 'path': relative, 'sha256': p.sha(p.local_file(root, relative)),
             'description': description, 'recorded_at': p.now()}
    if check:
        entry['check'] = check
    if origin:
        entry.update(origin=origin, accessed_at=accessed_at or p.now())
    verify_entry(root, entry, path)
    condition['method'] = method
    condition['evidence'].append(ident)
    condition['status'] = 'pending'
    data['evidence'][ident] = entry
    data['review'] = None
    data['status'] = 'in_progress'
    save_unchanged(path, data, task_digest)
    return {'status': 'created', 'evidence': ident, 'task': slug}


def review_template(root: Path, slug: str) -> dict:
    root = root.resolve()
    path = task_file(root, slug)
    data = p.load(path)
    review_path = path.parent / 'review.json'
    if review_path.exists():
        raise ValueError('review.json already exists; review it explicitly instead of overwriting')
    from .completion_review import template
    audit = template(data['kind'])
    audit['findings'] = [{'id': ident, 'summary': '', 'cause': '', 'status': 'open', 'regression': None}
                         for ident in data.get('findings', [])]
    p.atomic(review_path, {'version': 2, 'task_contract': contract(data),
                          'evidence_digest': p.signature(data['evidence']),
                          'reviewer': '', 'reviewer_type': 'agent', 'independent': False,
                          'criteria': [{'id': c['id'], 'decision': 'pending', 'reason': '',
                                        'evidence': c['evidence']} for c in data['acceptance']],
                          'limitations': [], 'blockers': [], 'verification': audit})
    return {'status': 'created', 'review': review_path.relative_to(root).as_posix()}


def assess(root: Path, path: Path, data: dict, review_path: str | None = None, *, require_current=True,
           allow_missing_runtime=False) -> list[str]:
    errors = []
    try:
        from .tasks import validate
        schema_errors = validate({**data, 'status': 'in_progress'}, root=root, task_path=path)
        if schema_errors:
            return schema_errors
        if data.get('version') != 2:
            raise ValueError('legacy task completion is unverified; migrate to version 2')
        for entry in data['evidence'].values():
            if (allow_missing_runtime and entry['path'].startswith('.runtime/')
                    and not inside(root, entry['path']).is_file()):
                continue
            verify_entry(root, entry, path, require_current=require_current)
        refs = [ref for c in data['acceptance'] for ref in c['evidence']]
        types = {data['evidence'][ref]['type'] for ref in refs}
        missing = REQUIRED[data['kind']] - types
        if missing:
            raise ValueError('missing work-type evidence: ' + ', '.join(sorted(missing)))
        review_ref = review_path or (data.get('review') or {}).get('path')
        if not review_ref:
            raise ValueError('a criterion-by-criterion review is required')
        rp = p.local_file(root, review_ref)
        if not review_path and p.sha(rp) != data['review'].get('sha256'):
            raise ValueError('completion review changed')
        review = p.load(rp)
        if (review.get('version') not in (1, 2) or review.get('task_contract') != contract(data)
                or review.get('evidence_digest') != p.signature(data['evidence'])):
            raise ValueError('review is stale for the task contract or evidence')
        if (not isinstance(review.get('reviewer'), str) or not review['reviewer'].strip()
                or review.get('reviewer_type') not in {'agent', 'human'}
                or not isinstance(review.get('independent'), bool)):
            raise ValueError('review must identify who reviewed and whether it was independent')
        if not isinstance(review.get('limitations'), list) or review.get('blockers') != []:
            raise ValueError('unresolved blockers prevent closure; record limitations separately')
        rows = review.get('criteria', [])
        if len(rows) != len(data['acceptance']) or {r['id'] for r in rows} != {c['id'] for c in data['acceptance']}:
            raise ValueError('review must cover every acceptance condition exactly once')
        for condition in data['acceptance']:
            row = next(r for r in rows if r['id'] == condition['id'])
            if (row.get('decision') != 'passed' or not isinstance(row.get('reason'), str) or not row['reason'].strip()
                    or not condition.get('method') or not condition['evidence']
                    or row.get('evidence') != condition['evidence']):
                raise ValueError('each condition needs an explicit passing reason and matching evidence IDs')
        if require_current and review['version'] != 2:
            raise ValueError('current completion requires a version-2 review with review rounds and regression records')
        if review['version'] == 2:
            from .completion_review import validate as validate_review
            validate_review(root, data, review.get('verification'), require_current=require_current,
                            allow_missing_runtime=allow_missing_runtime)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, StopIteration) as exc:
        errors.append(str(exc))
    return errors


def finish(root: Path, slug: str, *, review: str | None = None, complete=False) -> dict:
    root = root.resolve()
    path = task_file(root, slug)
    task_digest = p.sha(path)
    data = p.load(path)
    if not isinstance(data, dict):
        return {'status': 'needs_revision', 'errors': ['task must be an object'], 'task': slug}
    reference = data.get('review') if isinstance(data.get('review'), dict) else {}
    review_ref = review or reference.get('path')
    try:
        rp = p.local_file(root, review_ref) if review_ref else None
        review_digest = p.sha(rp) if rp else None
    except (OSError, ValueError, TypeError) as exc:
        return {'status': 'needs_revision', 'errors': [str(exc)], 'task': slug}
    errors = assess(root, path, data, review)
    try:
        if p.sha(path) != task_digest or (rp is not None and p.sha(rp) != review_digest):
            errors.append('task or review changed during verification; reassess the newer record')
    except OSError as exc:
        errors.append(str(exc))
    if errors:
        return {'status': 'needs_revision', 'errors': errors, 'task': slug}
    if complete:
        data.update(status='complete', completed_at=p.now(), review={'path': rp.relative_to(root).as_posix(), 'sha256': review_digest})
        for condition in data['acceptance']:
            condition['status'] = 'passed'
        try:
            save_unchanged(path, data, task_digest)
        except (OSError, ValueError) as exc:
            return {'status': 'needs_revision', 'errors': [str(exc)], 'task': slug}
    return {'status': 'passed', 'task': slug, 'complete': complete,
            'note': 'Evidence integrity and recorded review checked; this is not an independent truth judgment.'}
