"""Canonical project documents, selective bindings and bounded local updates."""
from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import tempfile

from . import document_indexes
from .core import inside, runtime_path
from .provenance import local_file

RESERVED = {'tasks', 'knowledge', 'projects'}
ROOT_DOCUMENTS = {'index.md', 'README.md', 'brief.md', 'security.md'}
SECTIONS = {'architecture', 'features', 'decisions', 'operations'}
KINDS = {'spec', 'design', 'verification'}
LIMIT = 2 * 1024 * 1024


def slug(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', value):
        raise ValueError('document names require lowercase hyphenated slugs')
    return value


def profiles(root):
    direct = [p for p in (root / 'docs').glob('*/workflow.toml') if p.parent.name not in RESERVED]
    return sorted(set(direct + list((root / 'docs/projects').glob('*/workflow.toml'))))


def settings(root, relative, data):
    value = data.get('documentation')
    if value is None:
        return False
    if not isinstance(value, dict) or set(value) != {'layout'} or value['layout'] != 'feature-folders':
        raise ValueError('documentation requires layout="feature-folders"')
    parts = Path(relative).parts
    if len(parts) != 3 or parts[0] != 'docs' or parts[1] in RESERVED or parts[2] != 'workflow.toml':
        raise ValueError('feature-folders requires docs/<project>/workflow.toml; migrate legacy profiles first')
    slug(parts[1])
    safe_target(root, relative)
    return True


def safe_target(root, relative):
    resolved = inside(root, relative)
    path = root
    for part in Path(relative).parts:
        path = path / part
        if path.is_symlink():
            raise ValueError('document paths must not use symlinks')
    return resolved


def inspect(root, relative, data):
    if not settings(root, relative, data):
        return {'errors': [], 'notes': [f'{relative}: legacy document placement; explicit reading remains supported']}
    folder = root / Path(relative).parent
    errors = []
    for file in (root / 'docs').iterdir():
        if file.is_file() and file.suffix.casefold() == '.md' and file.name not in {'index.md', 'README.md'}:
            errors.append(f'document placement: {file.relative_to(root)} needs a project folder')
    for file in folder.iterdir():
        rel = file.relative_to(root).as_posix()
        if file.is_file() and file.suffix.casefold() == '.md' and file.name not in ROOT_DOCUMENTS:
            errors.append(f'document placement: {rel} belongs in a feature or shared section folder')
        if file.is_dir() and file.name not in SECTIONS:
            errors.append(f'document placement: unexpected section {rel}')
    context = data.get('context', {})
    feature_root = folder / 'features'
    if feature_root.exists():
        for file in feature_root.rglob('*'):
            if not file.is_file() or file.suffix.casefold() != '.md' or file.name == 'index.md':
                continue
            rel = file.relative_to(root).as_posix()
            if len(file.relative_to(feature_root).parts) < 2:
                errors.append(f'document placement: {rel} requires a feature folder')
            rules = [r for r in context.get('rules', []) if rel in r.get('documents', [])]
            if rel in context.get('documents', []) or not any((r.get('paths') or r.get('topics')) and not r.get('kinds') for r in rules) or any(r.get('kinds') for r in rules):
                errors.append(f'document placement: {rel} needs selective context.rules paths/topics')
    return {'errors': errors, 'notes': []}


def _replace(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o644
    fd, temporary = tempfile.mkstemp(prefix='.document-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(text)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


@contextmanager
def _lock(root):
    path = runtime_path(root, '.runtime/document-write.lock')
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ValueError('another document writer is active') from exc
    try:
        os.close(fd)
        yield
    finally:
        path.unlink(missing_ok=True)


def _managed(text, marker, ending, block):
    count = text.count(marker)
    if not count:
        return text.rstrip() + '\n\n' + block
    if count != 1:
        raise ValueError('duplicate managed document binding')
    start = text.index(marker)
    stop = text.find(ending, start)
    if stop < 0:
        raise ValueError('unterminated managed document binding')
    stop += len(ending)
    if stop < len(text) and text[stop] == '\n':
        stop += 1
    return text[:start] + block + text[stop:]


def _binding(text, data, relative, paths, topics, role):
    from .workflows import validate_conditions
    rules = [r for r in data.get('context', {}).get('rules', []) if relative in r.get('documents', [])]
    marker = '# harness-document: ' + relative + '\n'
    ending = '# /harness-document'
    managed = marker in text
    if not paths and not topics and rules:
        paths = sorted(set(p for r in rules for p in r.get('paths', [])))
        topics = sorted(set(t for r in rules for t in r.get('topics', [])))
    paths, topics = sorted(set(paths)), sorted(set(topics))
    validate_conditions({'paths': paths, 'topics': topics}, 'document binding')
    if relative in data.get('context', {}).get('documents', []) or any(r.get('kinds') for r in rules):
        raise ValueError('feature documents require selective paths/topics without global or kind bindings')
    if rules and not managed:
        if len(rules) != 1 or paths != sorted(rules[0].get('paths', [])) or topics != sorted(rules[0].get('topics', [])):
            raise ValueError('existing manual document conditions differ; update that rule explicitly')
        return text
    block = marker + '[[context.rules]]\n'
    for key, value in [('paths', paths), ('topics', topics), ('documents', [relative]), ('when', role)]:
        if value:
            block += key + ' = ' + json.dumps(value, ensure_ascii=False) + '\n'
    block += ending + '\n'
    return _managed(text, marker, ending, block)


def upsert(root, profile, feature, kind, source, role, *, paths=(), topics=()):
    from . import workflows
    root = root.resolve()
    profile_file = local_file(root, profile)
    data = workflows.load(root, profile)
    if not settings(root, profile, data):
        raise ValueError('document writes require a canonical feature-folders profile')
    slug(feature)
    if kind not in KINDS:
        raise ValueError('document kind must be spec, design or verification')
    if (not isinstance(role, str) or len(role) > 500 or not role.strip()
            or any(c in role for c in '\r\n[]<>')):
        raise ValueError('document role must be one bounded line without Markdown links')
    if 'document.md' not in document_indexes.described_links(f'- [Document](document.md): {role}\n'):
        raise ValueError('document role needs an actual description')
    if any(not isinstance(t, str) or not t.strip() or len(t) > 128 or '\n' in t or '\r' in t for t in topics):
        raise ValueError('invalid document topic')
    with local_file(root, source).open('rb') as stream:
        raw = stream.read(LIMIT + 1)
    if len(raw) > LIMIT:
        raise ValueError('document source exceeds limit')
    body = raw.decode('utf-8')
    if not body.strip() or '\x00' in body:
        raise ValueError('document source must be nonempty UTF-8 Markdown')
    target_relative = (Path(profile).parent / 'features' / feature / (kind + '.md')).as_posix()
    target = safe_target(root, target_relative)
    if target.exists():
        local_file(root, target_relative)
    feature_folder = target.parent
    indexes = [feature_folder / 'index.md', feature_folder.parent / 'index.md', profile_file.parent / 'index.md', root / 'docs/index.md']
    targets = [target, profile_file, *indexes]
    for file in targets:
        safe_target(root, file.relative_to(root).as_posix())
        if file.exists():
            local_file(root, file.relative_to(root).as_posix())
    with _lock(root):
        # Read the contract again under the writer lock; do not overwrite a stale copy.
        current = workflows.load(root, profile)
        if not settings(root, profile, current):
            raise ValueError('document layout changed while preparing the update')
        original = {file: file.read_bytes() if file.exists() else None for file in targets}
        modes = {file: file.stat().st_mode & 0o777 for file in targets if file.exists()}
        created_dirs = [d for d in [feature_folder.parent, feature_folder] if not d.exists()]
        workflow_text = original[profile_file].decode('utf-8')
        changed_workflow = _binding(workflow_text, current, target_relative, list(paths), list(topics), role)
        index = indexes[0]
        text = original[index].decode('utf-8') if original[index] is not None else f'# {feature} 기능 문서\n'
        marker, ending = '<!-- harness-document: ' + target.name + ' -->\n', '<!-- /harness-document -->'
        if marker in text or target.name not in document_indexes.described_links(text):
            block = marker + f'- [{kind}]({target.name}): {role}\n' + ending + '\n'
            text = _managed(text, marker, ending, block)
        # Stage the same described-link folder maps as register_folder, so the
        # document, profile and every ancestor can be committed/rolled back together.
        writes = {target: body, index: text, profile_file: changed_workflow}
        child = feature_folder
        for parent_index in indexes[1:]:
            parent_text = original[parent_index].decode('utf-8') if original[parent_index] is not None else '# 문서 지도\n'
            link = child.name + '/index.md'
            mapped = {t.removeprefix('./') for t in document_indexes.described_links(parent_text)}
            if link not in mapped:
                parent_text = parent_text.rstrip() + f'\n\n- [{child.name}]({link}): 하위 문서의 정본과 읽을 조건\n'
            writes[parent_index] = parent_text
            child = child.parent
        written = {}
        try:
            for file, text in writes.items():
                current_bytes = file.read_bytes() if file.exists() else None
                if current_bytes != original[file]:
                    raise ValueError('document inputs changed while preparing the update')
                _replace(file, text)
                written[file] = text.encode('utf-8')
            workflows.load(root, profile)
        except Exception:
            for file in reversed(list(written)):
                # Preserve an independent edit made after this writer's output.
                if not file.exists() or file.read_bytes() != written[file]:
                    continue
                before = original[file]
                if before is None:
                    file.unlink(missing_ok=True)
                else:
                    _replace(file, before.decode('utf-8'))
                    os.chmod(file, modes[file])
            for directory in reversed(created_dirs):
                if directory.exists() and not any(directory.iterdir()):
                    directory.rmdir()
            raise
    return {'status': 'passed', 'document': target_relative,
            'updated': original[target] is not None, 'profile': profile,
            'note': 'Document, ancestor maps and selective binding updated. Meaning and applicability remain the agent responsibility.'}


def migration_plan(root, profile):
    from . import workflows
    root = root.resolve()
    local_file(root, profile)
    workflows.load(root, profile)
    parts = Path(profile).parts
    if len(parts) != 4 or parts[:2] != ('docs', 'projects') or parts[-1] != 'workflow.toml':
        raise ValueError('migration planning requires docs/projects/<project>/workflow.toml')
    slug(parts[2])
    if parts[2] in RESERVED:
        raise ValueError('legacy name conflicts with a reserved namespace')
    folder = root / Path(profile).parent
    destination = root / 'docs' / parts[2]
    if destination.exists():
        raise ValueError('canonical destination already exists; reconcile the two sources first')
    mapping = []
    for file in sorted(folder.rglob('*')):
        if file.is_symlink():
            raise ValueError('migration source contains symlinks')
        if file.is_file():
            mapping.append({'from': file.relative_to(root).as_posix(),
                            'to': (destination / file.relative_to(folder)).relative_to(root).as_posix(),
                            'needs_classification': file.parent == folder and file.suffix == '.md' and file.name not in ROOT_DOCUMENTS})
    return {'status': 'planned', 'mapping': mapping,
            'required_follow_up': ['classify loose documents into feature/shared folders',
                                   'update links, active profile/context references and indexes',
                                   'preserve original reports and review/evidence integrity; rerun checks'],
            'note': 'Read-only mapping only. No files, historical reports or external repositories were moved.'}
