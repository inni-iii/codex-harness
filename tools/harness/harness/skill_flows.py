"""Persistent skill-route control; agents perform work, existing evidence proves it.

This module never invokes a model, shell command, package manager or remote tool.
"""
from __future__ import annotations

from contextlib import contextmanager
import copy
import json
import os
from pathlib import Path
import re
import uuid

from . import context, evidence, flow_catalog as fc, provenance as p, reasons, tasks
from .core import runtime_path

LIMIT = 1024 * 1024


def path(root, run):
    fc.names([run], 'flow run ID')
    return runtime_path(root, f'.runtime/skill-flows/{run}.json')


@contextmanager
def locked(root, run):
    lock = path(root, run).with_suffix('.lock')
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise ValueError('flow is busy; preserve its lock and retry after the writer finishes') from None
    try:
        os.close(fd)
        yield
    finally:
        lock.unlink(missing_ok=True)


def task_data(root, slug):
    tp = evidence.task_file(root, slug)
    task = p.load(tp)
    if not isinstance(task, dict):
        raise ValueError('flow task must be an object')
    errors = tasks.validate({**task, 'status': 'in_progress'}, root=root, task_path=tp)
    if task.get('version') != 2 or errors:
        raise ValueError('flow requires a valid version-2 task')
    return tp, task


def sources(root, tp):
    return p.signature({rel: [digest, (root / rel).stat().st_mode & 0o111]
                        for rel, digest in p.snapshot(root).items() if not evidence.bookkeeping(rel, tp, root)})


def proof(root, task, tp, ids, *, require_current=True):
    if not isinstance(ids, list) or not ids or not all(isinstance(x, str) and x in task['evidence'] for x in ids) or len(set(ids)) != len(ids):
        raise ValueError('specify distinct existing task evidence IDs')
    result = {}
    for ident in ids:
        entry = task['evidence'][ident]
        evidence.verify_entry(root, entry, tp, require_current=require_current)
        result[ident] = p.signature(entry)
    return result


def check_proof(root, task, tp, recorded, *, require_current=True):
    if not isinstance(recorded, dict) or not recorded:
        raise ValueError('flow result has no bound evidence')
    if proof(root, task, tp, list(recorded), require_current=require_current) != recorded:
        raise ValueError('flow evidence binding changed')


def bindings(root, task, tp, route, supplied):
    if not isinstance(supplied, dict) or set(supplied) - set(route['inputs']) or 'request' in supplied:
        raise ValueError('unknown input or attempt to override task request')
    missing = set(route['inputs']) - {'request'} - set(supplied)
    if missing:
        raise ValueError('missing route inputs: ' + ', '.join(sorted(missing)))
    bound = {name: proof(root, task, tp, [ident]) for name, ident in supplied.items()}
    return {'request': evidence.contract(task), **bound}


def frame(root, task, tp, node, cat, supplied):
    bound = bindings(root, task, tp, cat['nodes'][node], supplied)
    reasons.check(root, task, tp, cat['nodes'][node], bound)
    return {'node': node, 'inputs': bound,
            'steps': [], 'validation': None, 'calls': {}, 'last_return': None, 'choice': None}


def progress(root, task, tp):
    # Metadata edits or freshly numbered copies of the same proof are not progress.
    return p.signature([sources(root, tp), evidence.contract(task),
                        sorted({entry['sha256'] for entry in task['evidence'].values()})])


def visit(state, node, fingerprint):
    record = state['visits'].get(node, {'fingerprint': fingerprint, 'count': 0})
    count = record['count'] + 1 if record['fingerprint'] == fingerprint else 1
    state['visits'][node] = {'fingerprint': fingerprint, 'count': count}
    if count > state['limits']['visits']:
        state.update(status='blocked', blocked_reason='same node revisited without new source, contract or evidence content')


def save(root, run, state, action, detail):
    state['revision'] += 1
    state['events'].append({'revision': state['revision'], 'at': p.now(), 'action': action,
                            'node': state['current']['node'], **detail})
    state.pop('integrity', None)
    state['integrity'] = p.signature(state)
    raw = json.dumps(state, ensure_ascii=False, allow_nan=False).encode()
    if len(raw) > LIMIT or len(state['events']) > 1000:
        raise ValueError('flow history reached its bound; retain this run and start a separately scoped task')
    p.atomic(path(root, run), state)


def read(root, run, cat):
    state = p.load(path(root, run), LIMIT)
    required = {'version', 'run', 'task', 'contract', 'catalog', 'entry', 'current', 'stack', 'status',
                'revision', 'moves', 'limits', 'visits', 'events', 'pending', 'blocked_reason', 'integrity'}
    fc.fields(state, required, required, 'flow state')
    digest = state['integrity']
    if p.signature({k: v for k, v in state.items() if k != 'integrity'}) != digest:
        raise ValueError('flow state integrity changed')
    if state['version'] != 1 or state['run'] != run or state['status'] not in {'running', 'waiting', 'blocked', 'finished', 'failed'}:
        raise ValueError('invalid flow state identity/status')
    fc.names([state['task']], 'flow task')
    for field in ['revision', 'moves']:
        if type(state[field]) is not int or state[field] < 0:
            raise ValueError('invalid flow counters')
    fc.fields(state['limits'], ['moves', 'depth', 'visits'], ['moves', 'depth', 'visits'], 'flow limits')
    if any(type(v) is not int or v < 1 or v > 1000 for v in state['limits'].values()) or state['limits']['depth'] > 16:
        raise ValueError('invalid flow limits')
    if not isinstance(state['stack'], list) or len(state['stack']) > state['limits']['depth'] or not isinstance(state['visits'], dict):
        raise ValueError('invalid flow stack/visits')
    if not isinstance(state['events'], list) or len(state['events']) > 1000 or state['revision'] != len(state['events']):
        raise ValueError('invalid flow event history')
    for i, event in enumerate(state['events'], 1):
        if not isinstance(event, dict) or event.get('revision') != i:
            raise ValueError('invalid event revision')
    frames = [state['current']]
    for call in state['stack']:
        fc.fields(call, ['frame', 'target', 'edge', 'failed_exit'], ['frame', 'target', 'edge', 'failed_exit'], 'call frame')
        frames.append(call['frame'])
    for f in frames:
        fc.fields(f, ['node', 'inputs', 'steps', 'validation', 'calls', 'last_return', 'choice'],
                  ['node', 'inputs', 'steps', 'validation', 'calls', 'last_return', 'choice'], 'route frame')
        if not isinstance(f['node'], str) or not fc.NODE.fullmatch(f['node']) or not isinstance(f['inputs'], dict) or not isinstance(f['steps'], list) or not isinstance(f['calls'], dict):
            raise ValueError('invalid route frame')
        if state['catalog'] == cat['digest']:
            route = cat['nodes'].get(f['node'])
            if route is None or len(f['steps']) > len(route['steps']):
                raise ValueError('invalid current route/steps')
            expected = [s['id'] for s in route['steps'][:len(f['steps'])]]
            if [s.get('id') for s in f['steps']] != expected:
                raise ValueError('flow steps are not an ordered prefix')
        if f['validation'] is not None and (not isinstance(f['validation'], dict) or f['validation'].get('result') not in {'passed', 'failed', 'blocked'}):
            raise ValueError('invalid validation outcome')
    if (state['status'] == 'waiting') != (state['pending'] is not None):
        raise ValueError('invalid waiting state')
    return state


def fresh(state, cat, task):
    if state['catalog'] != cat['digest'] or state['contract'] != evidence.contract(task):
        raise ValueError('route catalog or task contract changed; explicitly restart this flow with the current contract')


def complete(f, route):
    return len(f['steps']) == len(route['steps'])


def check_inputs(root, task, tp, f, *, require_current=True):
    if f['inputs'].get('request') != evidence.contract(task):
        raise ValueError('route request changed')
    for name, ident in f['inputs'].items():
        if name != 'request':
            check_proof(root, task, tp, ident, require_current=require_current)
    for step in f['steps']:
        check_proof(root, task, tp, step['evidence'], require_current=require_current)


def validated(root, task, tp, record, fingerprint):
    if not isinstance(record, dict) or record.get('result') != 'passed':
        raise ValueError('successful validation is required')
    check_proof(root, task, tp, record['evidence'])
    if record.get('sources') != fingerprint:
        raise ValueError('validation source state changed; re-enter and verify the changed result')


def guards(root, task, tp, f, edge, fingerprint):
    if 'validated' in edge['guards']:
        validated(root, task, tp, f['validation'], fingerprint)
    if 'failed' in edge['guards']:
        failures = [f['validation'], f['last_return']]
        if not any(isinstance(v, dict) and (v.get('result') in {'failed', 'blocked'}
                   or (v.get('result') == 'passed' and v.get('sources') != fingerprint)) for v in failures):
            raise ValueError('repair transition requires an observed failed/blocked result')


def view(root, state, cat, task, tp):
    f = state['current']; route = cat['nodes'].get(f['node'])
    stale = []
    try:
        fresh(state, cat, task)
        check_inputs(root, task, tp, f)
        if route:
            reasons.check(root, task, tp, route, f['inputs'])
        if f['validation'] and f['validation']['result'] == 'passed':
            validated(root, task, tp, f['validation'], sources(root, tp))
    except (OSError, ValueError) as exc:
        stale.append(str(exc))
    phase = 'decide' if f['validation'] else 'validate' if route and complete(f, route) else 'steps'
    return {'status': 'passed', 'flow_status': state['status'], 'run': state['run'], 'task': state['task'],
            'revision': state['revision'], 'node': f['node'], 'phase': phase,
            'completed_steps': [s['id'] for s in f['steps']], 'validation': f['validation'],
            'last_return': f['last_return'], 'stack': [{'caller': c['frame']['node'], 'target': c['target']} for c in state['stack']],
            'return_contract': ({'node': state['stack'][-1]['target'], 'evidence_types': cat['nodes'][state['stack'][-1]['target']]['evidence_types']}
                                if state['stack'] and state['stack'][-1]['target'] in cat['nodes'] else None),
            'pending': state['pending'], 'stale': stale, 'blocked_reason': state['blocked_reason'],
            'outgoing': fc.outgoing(cat, f['node']),
            'note': 'Flow position and declared evidence are checked; task acceptance and actual user authorship remain separate judgments.'}


def start(root, run, task_slug, node, *, inputs=None, max_moves=100, max_depth=8, max_visits=3):
    cat = fc.load(root)
    if node not in cat['nodes']:
        raise ValueError('unknown entry node')
    limits = {'moves': max_moves, 'depth': max_depth, 'visits': max_visits}
    if any(type(v) is not int or v < 1 or v > 1000 for v in limits.values()) or max_depth > 16:
        raise ValueError('flow limits must be positive and bounded; depth is at most 16')
    with locked(root, run):
        if path(root, run).exists():
            raise ValueError('flow already exists; inspect or restart explicitly')
        tp, task = task_data(root, task_slug)
        if task['status'] == 'complete':
            raise ValueError('start a flow on an open task')
        state = {'version': 1, 'run': run, 'task': task_slug, 'contract': evidence.contract(task),
                 'catalog': cat['digest'], 'entry': node, 'current': frame(root, task, tp, node, cat, inputs or {}),
                 'stack': [], 'status': 'running', 'revision': 0, 'moves': 0, 'limits': limits,
                 'visits': {}, 'events': [], 'pending': None, 'blocked_reason': None}
        visit(state, node, progress(root, task, tp))
        save(root, run, state, 'start', {})
        return view(root, state, cat, task, tp)


def inspect(root, run):
    cat = fc.load(root); state = read(root, run, cat)
    tp, task = task_data(root, state['task'])
    return view(root, state, cat, task, tp)


def act(root, run, action, *, step=None, result=None, reason=None, evidence_ids=None,
        edge_id=None, inputs=None, question=None, question_id=None, choice=None, node=None,
        expect_revision=None):
    cat = fc.load(root)
    with locked(root, run):
        state = read(root, run, cat)
        if expect_revision is not None and expect_revision != state['revision']:
            raise ValueError('flow revision changed; inspect before acting')
        tp, task = task_data(root, state['task'])
        if task['status'] == 'complete':
            raise ValueError('flow task is already complete')
        if action != 'restart':
            fresh(state, cat, task)
            if state['status'] not in {'running', 'waiting'}:
                raise ValueError('flow is not running; inspect its outcome before restarting')
            if state['status'] == 'waiting' and action not in {'answer', 'block'}:
                raise ValueError('flow is waiting for the current user answer')
        task_digest = p.sha(tp)
        f = state['current']; route = cat['nodes'].get(f['node'])
        fp = sources(root, tp)
        detail = {}
        if action == 'restart':
            fc.text(reason, 'restart reason')
            changed = (state['catalog'] != cat['digest'] or state['contract'] != evidence.contract(task)
                       or bool(view(root, state, cat, task, tp)['stale']))
            current_progress = progress(root, task, tp)
            old_visit = state['visits'].get(f['node'], {})
            if not changed and state['status'] not in {'blocked', 'failed'}:
                raise ValueError('restart is for a changed contract/catalog or a stopped flow')
            if not changed and old_visit.get('fingerprint') == current_progress:
                raise ValueError('restart needs new source, contract or evidence content')
            target = node or state['entry']
            if target not in cat['nodes']:
                raise ValueError('unknown restart node')
            state.update(contract=evidence.contract(task), catalog=cat['digest'], entry=target,
                         current=frame(root, task, tp, target, cat, inputs or {}), stack=[],
                         status='running', pending=None, blocked_reason=None)
            visit(state, target, current_progress)
            state['moves'] += 1; detail = {'reason': reason}
        else:
            repair = action == 'move' and 'failed' in cat['edges'].get(edge_id, {}).get('guards', [])
            check_inputs(root, task, tp, f, require_current=not repair)
            reasons.check(root, task, tp, route, f['inputs'])
            if action == 'step':
                if f['validation'] is not None or complete(f, route) or route['steps'][len(f['steps'])]['id'] != step:
                    raise ValueError('complete the next declared step once, in order')
                refs = proof(root, task, tp, evidence_ids or [])
                f['steps'].append({'id': step, 'evidence': refs}); detail = {'step': step, 'evidence': list(refs)}
            elif action == 'validate':
                if f['validation'] is not None or result not in {'passed', 'failed', 'blocked'}:
                    raise ValueError('validate once per entry; use a registered repair edge after failure')
                fc.text(reason, 'validation observation')
                refs = proof(root, task, tp, evidence_ids or [])
                if result == 'passed':
                    if not complete(f, route):
                        raise ValueError('steps_complete is not satisfied')
                    types = {task['evidence'][i]['type'] for i in refs}
                    required_types = set(route['evidence_types'])
                    if route['finish'] and state['stack'] and not state['stack'][-1]['failed_exit']:
                        required_types.update(cat['nodes'][state['stack'][-1]['target']]['evidence_types'])
                    if required_types - types:
                        raise ValueError('route validation is missing required evidence types')
                    reasons.check(root, task, tp, route, f['inputs'], result_ids=list(refs))
                    for target in route['required_calls']:
                        validated(root, task, tp, f['calls'].get(target), fp)
                if result == 'passed' and state['stack'] and f['node'] == state['stack'][-1]['target']:
                    state['stack'][-1]['failed_exit'] = None
                f['validation'] = {'result': result, 'reason': reason, 'evidence': refs, 'sources': fp}
                detail = {'result': result, 'reason': reason, 'evidence': list(refs)}
            elif action == 'move':
                edge = cat['edges'].get(edge_id)
                if edge is None or edge['from'] != f['node']:
                    raise ValueError('edge is not registered at the current node')
                guards(root, task, tp, f, edge, fp)
                if edge['when'] == 'steps_complete' and not complete(f, route):
                    raise ValueError('steps_complete is not satisfied')
                if edge['when'] == 'reason':
                    fc.text(reason, 'edge reason')
                if edge['when'] == 'user_choice':
                    answer = f['choice']
                    if not answer or answer['choice'] != edge['choice']:
                        raise ValueError('edge needs the matching current user choice')
                    check_proof(root, task, tp, answer['evidence'])
                supplied = dict(inputs or {})
                for name in set(cat['nodes'][edge['to']]['inputs']) - {'request'}:
                    if name not in supplied and name in f['inputs']:
                        supplied[name] = reasons.bound_id(f['inputs'], name)
                new = frame(root, task, tp, edge['to'], cat, supplied)
                if edge['mode'] == 'call':
                    active = {f['node'], *(c['frame']['node'] for c in state['stack']), *(c['target'] for c in state['stack'])}
                    if len(state['stack']) >= state['limits']['depth'] or edge['to'] in active:
                        raise ValueError('recursive call or maximum call depth reached')
                    caller = copy.deepcopy(f); caller['choice'] = None
                    state['stack'].append({'frame': caller, 'target': edge['to'], 'edge': edge['id'], 'failed_exit': None})
                elif state['stack'] and 'failed' in edge['guards'] and edge['from'] != edge['to']:
                    state['stack'][-1]['failed_exit'] = {'result': 'failed', 'reason': 'Called work left through a failure/replanning path; caller must reassess the requested result.'}
                state['current'] = new; state['moves'] += 1
                visit(state, edge['to'], progress(root, task, tp))
                detail = {'edge': edge['id'], 'mode': edge['mode'], 'from': edge['from'], 'reason': reason}
            elif action == 'ask':
                fc.text(question, 'question')
                choices = [e['choice'] for e in fc.outgoing(cat, f['node']) if e['when'] == 'user_choice']
                if not choices:
                    raise ValueError('current node has no user_choice edges')
                state['pending'] = {'id': uuid.uuid4().hex, 'question': question, 'choices': choices}
                f['choice'] = None; state['status'] = 'waiting'; detail = {'question_id': state['pending']['id']}
            elif action == 'answer':
                pending = state['pending']
                if not pending or pending['id'] != question_id or choice not in pending['choices']:
                    raise ValueError('answer must match the pending question ID and a registered choice')
                fc.text(reason, 'observed user answer')
                refs = proof(root, task, tp, evidence_ids or [])
                if not all(task['evidence'][i]['type'] in {'artifact', 'source'} for i in refs):
                    raise ValueError('user answer needs its source/artifact record')
                f['choice'] = {'question_id': question_id, 'choice': choice, 'evidence': refs}
                state['pending'] = None; state['status'] = 'running'
                detail = {'question_id': question_id, 'choice': choice, 'evidence': list(refs), 'reason': reason}
            elif action == 'finish':
                validation = f['validation']
                if not validation:
                    raise ValueError('finish needs an observed validation result')
                check_proof(root, task, tp, validation['evidence'])
                if validation['result'] == 'passed':
                    validated(root, task, tp, validation, fp)
                    if not route['finish']:
                        raise ValueError('this route must follow its successful continuation before finishing')
                if state['stack']:
                    call = state['stack'].pop(); caller = call['frame']
                    returned = {**validation, **(call['failed_exit'] or {}), 'requested_node': call['target'], 'finished_node': f['node']}
                    caller['calls'][call['target']] = returned; caller['last_return'] = returned
                    caller['validation'] = None; state['current'] = caller
                    state['moves'] += 1
                    detail = {'return_from': f['node'], 'requested_node': call['target'], 'result': returned['result']}
                else:
                    state['status'] = 'finished' if validation['result'] == 'passed' else 'failed' if validation['result'] == 'failed' else 'blocked'
                    state['blocked_reason'] = validation['reason'] if validation['result'] == 'blocked' else None
                    detail = {'result': validation['result']}
            elif action == 'block':
                fc.text(reason, 'blocked condition')
                state.update(status='blocked', pending=None, blocked_reason=reason); detail = {'reason': reason}
            else:
                raise ValueError('unknown flow action')
        if state['moves'] > state['limits']['moves']:
            state.update(status='blocked', pending=None, blocked_reason='flow movement budget exhausted')
        if p.sha(tp) != task_digest or sources(root, tp) != fp:
            raise ValueError('task or sources changed during flow update; inspect and retry against the new state')
        save(root, run, state, action, detail)
        return view(root, state, cat, task, tp)


def selected_context(root, run, *, read_contents=False, workflow=None):
    cat = fc.load(root); state = read(root, run, cat)
    tp, task = task_data(root, state['task']); fresh(state, cat, task)
    route = cat['nodes'][state['current']['node']]
    base = context.select(root, route['kind'], task.get('scope', []), [], workflow=workflow, read=read_contents)
    # Preserve project/index/security and adopted knowledge; do not preload target procedures.
    chosen = [d for d in base['documents'] if not d['path'].startswith('.agents/skills/')
              or d['path'].startswith('.agents/skills/security-review/')]
    selected = {d['path'] for d in chosen}
    for relative in [route['entrypoint'], *route['documents']]:
        if relative not in selected:
            record = {'path': relative, 'reasons': ['current skill route procedure']}
            if read_contents:
                record['content'] = p.local_file(root, relative).read_text()
            chosen.append(record); selected.add(relative)
    design_document = (reasons.selected_document(root, task, tp, state['current']['inputs'])
                       if set(route.get('entry_checks', [])) & {'design', 'alignment'} else None)
    if design_document and design_document['path'] not in selected:
        if not read_contents:
            design_document.pop('content', None)
        chosen.append(design_document)
    return {'status': 'planned', 'node': state['current']['node'], 'route': route, 'documents': chosen,
            'outgoing': [{**e, 'target_when': cat['nodes'][e['to']]['when']} for e in fc.outgoing(cat, state['current']['node'])],
            'security_review': base.get('security_review'),
            'note': 'Only current procedures and required project/security context are read; outgoing targets are metadata. No link expansion or automatic work execution.'}
