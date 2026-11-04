"""Opt-in independence from task records; full provenance is always retained."""
from pathlib import Path
import tomllib


def is_record(relative):
    parts = Path(relative).parts
    return (len(parts) >= 3 and parts[:2] == ('docs', 'tasks')
            and (Path(relative).suffix.casefold() == '.md' or parts[-1] in {'task.json', 'review.json'}))


def policy(root, checks, workflow=None):
    behavior = [c for c in checks if c['id'] != 'doctor' and c.get('covers_behavior', True)]
    if not behavior or not all(c.get('ignore_task_records', False) for c in behavior):
        return None
    protected = {path for check in behavior for path in check['paths']}
    if workflow:
        from .core import inside
        with inside(root, workflow).open('rb') as stream:
            data = tomllib.load(stream)
        def references(value):
            if isinstance(value, dict):
                for item in value.values(): references(item)
            elif isinstance(value, list):
                for item in value: references(item)
            elif isinstance(value, str) and value.startswith('docs/tasks/'):
                protected.add(value)
        references(data)
    return {'version': 1, 'record_inputs': sorted(protected)}


def select(mapping, value, *, protected=()):
    if value is None:
        return mapping
    from .core import matches, validate_patterns
    if (not isinstance(value, dict) or set(value) != {'version', 'record_inputs'}
            or type(value['version']) is not int or value['version'] != 1):
        raise ValueError('unknown verification record policy')
    validate_patterns(value['record_inputs'], 'verification record inputs')
    patterns = [*value['record_inputs'], *protected]
    return {rel: digest for rel, digest in mapping.items()
            if not is_record(rel) or matches(rel, patterns)}


def task_inputs(root, task_path):
    from . import provenance as p
    task = p.load(task_path)
    folder = task_path.parent.resolve().relative_to(root.resolve()).as_posix()
    return [folder + '/**', *task.get('scope', []), *task.get('inputs', []),
            *[entry['path'] for entry in task.get('evidence', {}).values()],
            *['docs/tasks/' + name + '/**' for name in task.get('depends_on', [])]]
