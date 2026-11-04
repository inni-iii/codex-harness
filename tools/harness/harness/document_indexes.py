"""Small folder maps: inspect names and index text, never document bodies."""
from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import re
import tempfile
import time
from urllib.parse import unquote, urlsplit

from .core import inside, runtime_path

ROOTS = ('docs', 'tools/harness/docs')
LINK = re.compile(r'(?<!!)\[[^\]\n]+\]\(\s*(?:<([^>\n]+)>|([^\s)]+))(?:\s+"[^"\n]*")?\s*\)')
PLACEHOLDERS = {'todo', 'tbd', 'pending', '작성 필요', '설명 필요', '미정'}


def prose(text: str) -> list[str]:
    text = re.sub(r'<!--[\s\S]*?-->', '', text)
    result, fence = [], None
    for line in text.splitlines():
        marker = re.match(r'^\s*(`{3,}|~{3,})', line)
        if marker:
            token = marker[1]
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            continue
        if fence is None:
            result.append(re.sub(r'(`+).*?\1', '', line))
    return result


def described_links(text: str) -> list[str]:
    """Recognize inline Markdown links with separate same-line role text.

    Tables and bullet entries are supported. A role must contain words beyond
    link labels; semantics still require a document review.
    """
    result = []
    for line in prose(text):
        links = list(LINK.finditer(line))
        description = LINK.sub('', line).strip(' |:-*#>\t')
        if (not re.search(r'[^\W_]{2}', description, re.UNICODE)
                or description.casefold() in PLACEHOLDERS):
            continue
        result.extend(match[1] or match[2] for match in links)
    return result


def inspect(root: Path) -> dict:
    errors, count = [], 0
    root = root.resolve()
    for relative in ROOTS:
        base = root / relative
        if base.is_symlink():
            errors.append(f'document index: symlink documentation root: {relative}')
            continue
        if not base.exists():
            continue
        if not base.is_dir():
            errors.append(f'document index: documentation root is not a directory: {relative}')
            continue
        def unreadable(error):
            raise error
        try:
            for parent, directories, names in os.walk(base, followlinks=False, onerror=unreadable):
                folder = Path(parent)
                count += 1
                for name in list(directories):
                    if (folder / name).is_symlink():
                        errors.append(f'document index: symlink folder: {(folder / name).relative_to(root)}')
                        directories.remove(name)
                directories.sort()
                index = folder / 'index.md'
                rel_index = index.relative_to(root).as_posix()
                if index.is_symlink():
                    errors.append(f'document index: symlink index: {rel_index}')
                    continue
                if not index.is_file():
                    errors.append(f'document index: missing {rel_index}')
                    continue
                text = index.read_text(encoding='utf-8')
                mapped = set()
                for target in described_links(text):
                    parts = urlsplit(target)
                    if parts.scheme or parts.netloc or not parts.path:
                        continue
                    destination = (folder / unquote(parts.path)).resolve()
                    if not destination.is_relative_to(root):
                        errors.append(f'document index: outside link in {rel_index}: {target}')
                    elif not destination.is_file():
                        errors.append(f'document index: stale link in {rel_index}: {target}')
                    else:
                        mapped.add(destination)
                expected = [folder / name for name in sorted(names)
                            if Path(name).suffix.casefold() == '.md' and name != 'index.md']
                expected += [folder / name / 'index.md' for name in directories]
                for document in expected:
                    if document.is_symlink():
                        errors.append(f'document index: symlink document: {document.relative_to(root)}')
                    elif document.resolve() not in mapped:
                        errors.append(f'document index: {rel_index} needs a link and role description for {document.relative_to(folder).as_posix()}')
        except (OSError, UnicodeError, ValueError) as exc:
            errors.append(f'document index: cannot inspect {relative}: {exc}')
    return {'status': 'failed' if errors else 'passed', 'folders': count, 'errors': errors}


def ancestors(root: Path, relative: str) -> list[str]:
    """Only maps on the path to an already selected document, no siblings."""
    document = Path(relative)
    for base in map(Path, ROOTS):
        if document.is_relative_to(base):
            result = []
            for length in range(len(base.parts), len(document.parts)):
                index = (Path(*document.parts[:length]) / 'index.md').as_posix()
                if index != relative and (root / index).is_file():
                    result.append(index)
            return result
    return []


@contextmanager
def _writer(root: Path):
    # Share the existing project-document writer namespace: both update ancestor maps.
    lock = runtime_path(root, '.runtime/document-write.lock')
    lock.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + 5
    while True:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            identity = os.fstat(fd)
            os.close(fd)
            break
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise ValueError('another document writer is active; preserve its lock and retry') from None
            time.sleep(.02)
    try:
        yield
    finally:
        try:
            current = lock.stat()
        except FileNotFoundError:
            current = None
        if current and (current.st_dev, current.st_ino) == (identity.st_dev, identity.st_ino):
            lock.unlink()


def _replace(index: Path, text: str) -> None:
    mode = index.stat().st_mode & 0o777 if index.exists() else 0o644
    fd, name = tempfile.mkstemp(prefix='.document-index-', dir=index.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(text)
        os.chmod(name, mode)
        os.replace(name, index)
    finally:
        Path(name).unlink(missing_ok=True)


def register_folder(root: Path, folder: Path, label: str, role: str) -> None:
    """Serialize all ancestor-map edits with existing document writers."""
    root = root.resolve()
    with _writer(root):
        _register_folder(root, folder, label, role)


def _register_folder(root: Path, folder: Path, label: str, role: str) -> None:
    """Connect a newly generated project/task without replacing user prose."""
    root = root.resolve()
    folder = folder.resolve()
    relative = folder.relative_to(root)
    base = next((Path(name) for name in ROOTS if relative.is_relative_to(name)), None)
    if base is None or relative == base:
        return
    parent = folder.parent
    index = inside(root, (parent / 'index.md').relative_to(root).as_posix())
    if (parent / 'index.md').is_symlink():
        raise ValueError('document index symlinks are unsupported')
    text = index.read_text() if index.exists() else '# 문서 지도\n'
    target = folder.name + '/index.md'
    existing = {unquote(urlsplit(link).path).removeprefix('./') for link in described_links(text)}
    if target not in existing:
        _replace(index, text.rstrip() + f'\n\n- [{label}]({target}): {role}\n')
    _register_folder(root, parent, parent.name, '하위 문서의 역할과 읽을 조건을 고르는 지도')
