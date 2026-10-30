"""Local worktree isolation and integration rehearsal; never commit or publish."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess

from . import checks
from .core import changed_paths, inside, validate_patterns, write_json


def run(root: Path, *args: str, allow_failure=False):
    result = subprocess.run(
        ['git', '--no-optional-locks', '-c', f'core.hooksPath={os.devnull}', '-c', 'rerere.enabled=false', *args],
        cwd=root, capture_output=True, text=True, timeout=60, check=False)
    if result.returncode and not allow_failure:
        raise ValueError(result.stderr.strip() or 'Git operation failed')
    return result


def slug_name(value: str) -> str:
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', value):
        raise ValueError('Workspace name must be a lowercase hyphenated slug')
    return value


def commit(root: Path, ref: str) -> str:
    result = run(root, 'rev-parse', '--verify', '--end-of-options', ref + '^{commit}', allow_failure=True)
    if result.returncode:
        raise ValueError('A committed base/ref is required; preserve current changes and establish a baseline first. No automatic staging or commit is performed.')
    return result.stdout.strip()


def entries(root: Path) -> list[dict]:
    data = run(root, 'worktree', 'list', '--porcelain', '-z').stdout
    records, current = [], {}
    for item in data.split('\0'):
        if not item:
            if current:
                records.append(current)
                current = {}
        else:
            key, _, value = item.partition(' ')
            current[key] = value
    if current:
        records.append(current)
    return records


def status(root: Path) -> dict:
    top = Path(run(root, 'rev-parse', '--show-toplevel').stdout.strip()).resolve()
    if top != root.resolve():
        raise ValueError('Run workspace commands from the repository root')
    common = Path(run(root, 'rev-parse', '--path-format=absolute', '--git-common-dir').stdout.strip()).resolve()
    own = Path(run(root, 'rev-parse', '--path-format=absolute', '--git-dir').stdout.strip()).resolve()
    return {'status': 'planned', 'isolated': common != own,
            'head': run(root, 'rev-parse', '--verify', 'HEAD', allow_failure=True).stdout.strip() or None,
            'branch': run(root, 'branch', '--show-current').stdout.strip() or None,
            'worktrees': entries(root), 'note': 'Isolation is per checkout; ports, databases, browser profiles and dependencies need separate project setup.'}


def clean_inputs(root: Path, commits: set[str], exclude: Path | None = None):
    for entry in entries(root):
        directory = Path(entry['worktree'])
        if entry.get('HEAD') not in commits or (exclude and directory.resolve() == exclude.resolve()):
            continue
        result = run(directory, 'status', '--porcelain', '--untracked-files=normal')
        if result.stdout:
            raise ValueError('An input checkout has uncommitted changes. They would be omitted; preserve and finish that work before preparing an integration.')


def location(root: Path, name: str) -> Path:
    slug_name(name)
    state = status(root)
    if state['isolated']:
        raise ValueError('Already in a linked worktree. Reuse its isolation; prepare new workspaces from the main checkout.')
    directory = inside(root, '.worktrees/' + name)
    if directory.exists():
        raise ValueError('Workspace path already exists; inspect and reuse it explicitly instead of overwriting it')
    ignored = run(root, 'check-ignore', '--no-index', '-q', '--', '.worktrees/' + name, allow_failure=True)
    if ignored.returncode:
        raise ValueError('Add .worktrees/ to the repository .gitignore before creating a workspace')
    return directory


def start(root: Path, name: str, base: str, goal: str, scope: list[str]) -> dict:
    if not goal.strip():
        raise ValueError('A meaningful work-unit goal is required')
    validate_patterns(scope, 'workspace scope')
    base_commit = commit(root, base)
    directory = location(root, name)
    if run(root, 'status', '--porcelain', '--untracked-files=normal').stdout:
        raise ValueError('Source checkout has uncommitted changes; establish a clean baseline first. No changes are copied or discarded.')
    record = inside(root, '.runtime/sessions/' + slug_name(name) + '.json')
    if record.exists():
        raise ValueError('Session record already exists; use another work-unit name')
    branch = 'harness/' + name
    run(root, 'worktree', 'add', '-b', branch, str(directory), base_commit)
    data = {'version': 1, 'status': 'created', 'goal': goal, 'scope': scope,
            'base_commit': base_commit, 'branch': branch, 'workspace': directory.relative_to(root).as_posix(),
            'created_at': datetime.now(timezone.utc).isoformat(),
            'note': 'Open the coding session in this workspace. No dependencies, private environment files or browser sessions were copied. Scope is intent, not a file lock.'}
    write_json(record, data)
    return data


def paths_between(root: Path, base: str, tip: str) -> list[str]:
    return sorted(p for p in run(root, 'diff', '--no-renames', '--name-only', '-z', base, tip).stdout.split('\0') if p)


def prepare(root: Path, name: str, source: str, target: str, goal: str, acceptance: list[str]) -> dict:
    slug_name(name)
    if not goal.strip() or not acceptance or not all(c.strip() for c in acceptance):
        raise ValueError('Integration requires a work-unit goal and acceptance conditions for both changes')
    target_commit, source_commit = commit(root, target), commit(root, source)
    clean_inputs(root, {target_commit, source_commit})
    base = run(root, 'merge-base', target_commit, source_commit).stdout.strip()
    directory = location(root, 'integration-' + name)
    output = inside(root, '.runtime/integrations/' + name)
    output.mkdir(parents=True, exist_ok=False)
    target_paths, source_paths = paths_between(root, base, target_commit), paths_between(root, base, source_commit)
    run(root, 'worktree', 'add', '--detach', str(directory), target_commit)
    merged = run(directory, 'merge', '--no-commit', '--no-ff', '--no-edit', source_commit, allow_failure=True)
    conflicts = unresolved(directory)
    if merged.returncode and not conflicts:
        # Keep the review workspace and log for diagnosis; never delete work automatically.
        (output / 'merge.log').write_text(merged.stdout + merged.stderr, encoding='utf-8')
        raise ValueError('Integration preparation failed; inspect the preserved review workspace and merge.log')
    overlap = sorted(set(target_paths) & set(source_paths))
    data = {'version': 1, 'status': 'needs_resolution' if conflicts else 'prepared',
            'goal': goal, 'acceptance': acceptance, 'source_ref': source, 'target_ref': target,
            'source_commit': source_commit, 'target_commit': target_commit, 'base_commit': base,
            'workspace': directory.relative_to(root).as_posix(), 'target_paths': target_paths,
            'source_paths': source_paths, 'overlapping_paths': overlap, 'conflicts': conflicts,
            'review_required': True, 'product_accepted': False}
    write_json(output / 'integration.json', data)
    (output / 'merge.log').write_text(merged.stdout + merged.stderr, encoding='utf-8')
    lines = ['# 통합 검토', '', f'목표: {goal}', '', '## 양쪽 요구', '']
    lines += ['- ' + condition for condition in acceptance]
    lines += ['', '## 변경 의도와 처리', '', '| 경로 | 작업 쪽 | 의도·최종 처리·이유·근거 |', '|---|---|---|']
    for path in sorted(set(target_paths) | set(source_paths)):
        side = '양쪽' if path in overlap else ('target' if path in target_paths else 'source')
        lines.append(f'| {path.replace(chr(124), chr(92) + chr(124))} | {side} | 미검토 |')
    lines += ['', '## 공유 경계·호출자', '', '겹치지 않는 파일의 API·권한·상태·설정 충돌도 대조한다.',
              '', '## 결정이 필요한 충돌', '', '양쪽 의도·양립 불가 이유·선택별 영향·추천안을 기록하고 결정 전에 사용자에게 알린다.',
              '', '## 합친 결과 검증', '', '실제 검사 범위·명령·대상 상태·결과·미확인을 기록한다. 테스트 통과만으로 위 검토를 완료 처리하지 않는다.', '']
    (output / 'review.md').write_text('\n'.join(lines), encoding='utf-8')
    return {**data, 'review': (output / 'review.md').relative_to(root).as_posix()}


def unresolved(root: Path) -> list[str]:
    return sorted(p for p in run(root, 'diff', '--name-only', '--diff-filter=U', '-z').stdout.split('\0') if p)


def load(root: Path, name: str) -> tuple[dict, Path]:
    record = inside(root, '.runtime/integrations/' + slug_name(name) + '/integration.json')
    data = json.loads(record.read_text())
    directory = inside(root, data['workspace'])
    parts = Path(data['workspace']).parts
    if len(parts) != 2 or parts[0] != '.worktrees' or not parts[1].startswith('integration-'):
        raise ValueError('Invalid integration workspace')
    if status(root)['worktrees'] == [] or directory not in [Path(e['worktree']) for e in entries(root)]:
        raise ValueError('Integration worktree is no longer registered')
    return data, directory


def stale(root: Path, data: dict, directory: Path) -> bool:
    if commit(directory, 'HEAD') != data['target_commit']:
        return True
    for side in ['source', 'target']:
        if commit(root, data[side + '_ref']) != data[side + '_commit']:
            return True
    try:
        clean_inputs(root, {data['target_commit'], data['source_commit']}, exclude=directory)
    except ValueError:
        return True
    return False


def inspect_integration(root: Path, name: str) -> dict:
    data, directory = load(root, name)
    conflicts = unresolved(directory)
    state = 'stale' if stale(root, data, directory) else ('needs_resolution' if conflicts else 'planned')
    return {**data, 'status': state, 'conflicts': conflicts, 'review_required': True}


def verify(root: Path, name: str, *, full=False, plan=False, workflow=None) -> dict:
    data, directory = load(root, name)
    state = inspect_integration(root, name)
    if state['status'] != 'planned':
        return state
    diff_check = run(directory, 'diff', '--check', data['base_commit'], allow_failure=True)
    if diff_check.returncode:
        return {**state, 'status': 'needs_resolution', 'diff_check': diff_check.stdout + diff_check.stderr}
    # Both work units must be covered, including target changes already in its HEAD.
    paths = sorted(set(data['target_paths']) | set(data['source_paths']) | set(changed_paths(directory)))
    result = checks.plan(directory, paths, full, workflow, checkpoint='integration') if plan else checks.run(directory, paths, full=full, workflow=workflow, checkpoint='integration')
    if plan:
        result['status'] = 'needs_configuration' if result['uncovered_paths'] or result['configuration_pending'] else 'planned'
    elif result['status'] == 'passed':
        result['status'] = 'checks_passed_review_pending'
    if stale(root, data, directory):
        result['status'] = 'stale'
    result.update({'integration': name, 'source_commit': data['source_commit'], 'target_commit': data['target_commit'],
                   'review_required': True, 'product_accepted': False})
    if not plan:
        write_json(inside(root, '.runtime/integrations/' + name + '/verification.json'), result)
    return result
