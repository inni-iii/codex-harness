"""Content-only document baselines for conditional flow completion; no Git diff."""
from pathlib import Path
import re

from . import provenance as p
from .core import canonical_relative, files


def includes(relative):
    path = Path(relative)
    if path.is_relative_to('docs/tasks'):
        return False
    return (path.is_relative_to('docs') or path.is_relative_to('tools/harness/docs')
            or path.suffix.casefold() in {'.md', '.mdx', '.rst', '.adoc'}
            or path.name.casefold().endswith('.md.tmpl'))


def snapshot(root):
    return {path.relative_to(root).as_posix(): p.sha(path) for path in files(root)
            if includes(path.relative_to(root).as_posix())}


def validate(root, baseline):
    if baseline is None:
        return  # Older frames have no trustworthy before-state.
    if not isinstance(baseline, dict):
        raise ValueError('invalid document baseline')
    for relative, digest in baseline.items():
        if (not isinstance(relative, str) or canonical_relative(root, relative) != relative
                or not includes(relative) or not isinstance(digest, str)
                or re.fullmatch('[a-f0-9]{64}', digest) is None):
            raise ValueError('invalid document baseline entry')


def changes(root, baseline):
    validate(root, baseline)
    if baseline is None:
        return {'available': False, 'unchanged': False, 'changed_paths': []}
    current = snapshot(root)
    changed = sorted(path for path in set(baseline) | set(current)
                     if baseline.get(path) != current.get(path))
    return {'available': True, 'unchanged': not changed, 'changed_paths': changed}
