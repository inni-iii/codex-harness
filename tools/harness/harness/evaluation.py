"""Evaluate saved task outcomes without starting models or inventing usage data."""
from __future__ import annotations

from pathlib import Path
import uuid

from . import evidence, provenance as p, tasks


def run(root: Path, suite: str, label: str) -> dict:
    root = root.resolve()
    spec = p.load(p.local_file(root, suite))
    if spec.get('version') != 1 or spec.get('evaluation_type') not in {'fixture', 'author_pilot', 'agent_benchmark'}:
        raise ValueError('declare a version-1 evaluation type explicitly')
    for key in ('population', 'limitations'):
        if not isinstance(spec.get(key), str) or not spec[key].strip():
            raise ValueError('evaluation suite needs ' + key)
    cases = spec.get('cases')
    if not isinstance(cases, list) or not cases:
        raise ValueError('evaluation suite needs cases')
    results, seen, task_names = [], set(), set()
    for case in cases:
        if (not isinstance(case, dict) or not isinstance(case.get('id'), str) or not case['id']
                or case['id'] in seen or case.get('kind') not in tasks.KINDS):
            raise ValueError('evaluation cases need unique IDs and valid work kinds')
        seen.add(case['id'])
        if not isinstance(case.get('task'), str) or case['task'] in task_names:
            raise ValueError('evaluation task names must be present and unique; duplicates are not independent samples')
        task_names.add(case['task'])
        errors, reviewer = [], None
        try:
            path = evidence.task_file(root, case['task'])
            data = p.load(path)
            if data['kind'] != case['kind'] or data['status'] != 'complete':
                errors.append('task kind/status does not match the evaluation case')
            errors.extend(tasks.validate(data, root=root, task_path=path))
            if not errors:
                review = p.load(p.local_file(root, data['review']['path']))
                reviewer = {key: review[key] for key in ('reviewer', 'reviewer_type', 'independent')}
                if spec['evaluation_type'] == 'agent_benchmark' and not reviewer['independent']:
                    errors.append('agent benchmark requires an independent recorded review')
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors.append(str(exc))
        results.append({'case': case['id'], 'kind': case['kind'], 'task': case['task'],
                        'status': 'failed' if errors else 'passed', 'errors': errors, 'review': reviewer})
    report = {'version': 1, 'record_type': 'task_evaluation', 'created_at': p.now(),
              'status': 'passed' if all(r['status'] == 'passed' for r in results) else 'failed',
              'label': label, 'evaluation_type': spec['evaluation_type'], 'population': spec['population'],
              'limitations': spec['limitations'], 'suite_sha256': p.sha(p.local_file(root, suite)),
              'cases': results, 'total': len(results), 'passed': sum(r['status'] == 'passed' for r in results),
              'product_accepted': False, 'usage': None,
              'note': 'Saved task-evidence assessment; runtime/token usage and independent quality gains are not inferred.'}
    path = root / '.runtime/evaluations' / (uuid.uuid4().hex + '.json')
    p.atomic(path, report)
    return {**report, 'report': path.relative_to(root).as_posix()}
