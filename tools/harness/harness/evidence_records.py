"""Batch mechanical record preparation; acceptance remains a reviewer decision."""
from __future__ import annotations

import re
from pathlib import Path

from . import evidence, provenance as p


def import_entries(root: Path, slug: str, manifest: str) -> dict:
    root = root.resolve()
    path = evidence.task_file(root, slug)
    digest = p.sha(path)
    data = p.load(path)
    from .tasks import validate
    if not isinstance(data, dict) or data.get('version') != 2 or data.get('status') == 'complete':
        raise ValueError('batch evidence requires an open version-2 task')
    errors = validate(data, root=root, task_path=path)
    if errors:
        raise ValueError('invalid task record: ' + '; '.join(errors))
    source = p.load(p.local_file(root, manifest))
    if (not isinstance(source, dict) or set(source) != {'version', 'entries'}
            or type(source['version']) is not int or source['version'] != 1
            or not isinstance(source['entries'], list) or not 1 <= len(source['entries']) <= 256):
        raise ValueError('manifest needs version 1 and 1..256 entries')
    allowed = {'id', 'type', 'path', 'criteria', 'description', 'check', 'origin', 'accessed_at'}
    registered = []
    for row in source['entries']:
        if not isinstance(row, dict) or set(row) - allowed:
            raise ValueError('unsupported evidence manifest fields')
        ident, criteria = row.get('id'), row.get('criteria')
        if (not isinstance(ident, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*', ident)
                or ident in data['evidence']):
            raise ValueError('evidence ID must be new and simple')
        if (not isinstance(criteria, list) or not criteria or not all(isinstance(c, str) for c in criteria)
                or len(criteria) != len(set(criteria))):
            raise ValueError('each entry needs distinct acceptance IDs')
        conditions = [next((c for c in data['acceptance'] if c['id'] == cid), None) for cid in criteria]
        if any(c is None or not isinstance(c.get('method'), str) or not c['method'].strip() for c in conditions):
            raise ValueError('set an existing acceptance ID and verification method before importing evidence')
        entry = {k: row[k] for k in ['type', 'path', 'description', 'check', 'origin', 'accessed_at'] if k in row}
        if not isinstance(entry.get('path'), str) or entry.get('type') not in evidence.TYPES:
            raise ValueError('evidence needs a supported type and repository-relative path')
        entry.update(sha256=p.sha(p.local_file(root, entry['path'])), recorded_at=p.now())
        if entry['type'] == 'source':
            # No invented historical access date: use the explicitly supplied date or registration time.
            entry.setdefault('accessed_at', entry['recorded_at'])
        evidence.verify_entry(root, entry, path)
        data['evidence'][ident] = entry
        for condition in conditions:
            condition['evidence'].append(ident)
            condition['status'] = 'pending'
        registered.append(ident)
    data.update(status='in_progress', review=None)
    # No on-disk task change until every row is checked. Keep the existing one-writer/optimistic contract.
    evidence.save_unchanged(path, data, digest)
    return {'status': 'created', 'task': slug, 'evidence': registered,
            'note': 'All entries validated before one task write; acceptance decisions remain pending.'}


def observations(root: Path, data: dict, task_path: Path) -> list[dict]:
    """Bound facts only, without raw logs, source text, or a truth/acceptance claim."""
    rows = []
    for ident, entry in data['evidence'].items():
        evidence.verify_entry(root, entry, task_path, require_current=False)
        row = {'id': ident, 'type': entry['type'], 'path': entry['path'], 'sha256': entry['sha256']}
        if entry['type'] == 'check':
            report = p.load(p.local_file(root, entry['path']))
            selected = next(r for r in report['results'] if r['check'] == entry['check'])
            row.update(check=entry['check'], status=selected['status'], checkpoint=report.get('checkpoint'),
                       current_sources='not_checked',
                       **{k: selected.get(k) for k in ['test_count', 'failed_count', 'skipped_count', 'duration_seconds', 'reused']})
        rows.append(row)
    return rows


def inspect(root: Path, slug: str) -> dict:
    root = root.resolve()
    path = evidence.task_file(root, slug)
    data = p.load(path)
    return {'status': 'observed', 'task': slug, 'observations': observations(root, data, path),
            'note': 'Content/log integrity checked; source currency, acceptance and independent review are not inferred.'}
