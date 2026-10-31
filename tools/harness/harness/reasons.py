"""Bound REASONS documents and scoped alignment reviews; no semantic auto-approval."""
from __future__ import annotations

import re
from pathlib import Path

from . import evidence, provenance as p
from .core import inside, matches, strict_json, validate_patterns

SECTIONS = ('requirements', 'entities', 'approach', 'structure', 'operations', 'norms', 'safeguards')
CHECKS = {'design', 'alignment'}
LIMIT = 1024 * 1024
ID = re.compile(r'[A-Za-z][A-Za-z0-9_-]{0,63}')


def fields(value, allowed, required, label):
    if not isinstance(value, dict) or set(value) - set(allowed) or set(required) - set(value):
        raise ValueError('invalid ' + label + ' fields')


def text(value, label):
    if not isinstance(value, str) or not value.strip() or len(value) > 4000:
        raise ValueError(label + ' requires concrete, bounded text')


def ids(values, label, *, empty=False):
    if (not isinstance(values, list) or (not empty and not values)
            or not all(isinstance(v, str) and ID.fullmatch(v) for v in values)
            or len(set(values)) != len(values)):
        raise ValueError('invalid ' + label)
    return values


def document(root, entry):
    if not isinstance(entry, dict) or entry.get('type') != 'artifact':
        raise ValueError('design input requires an artifact evidence record')
    path = p.local_file(root, entry['path'])
    if path.suffix != '.md' or path.stat().st_size > LIMIT or p.sha(path) != entry['sha256']:
        raise ValueError('design needs a current bounded Markdown artifact')
    content = path.read_text()
    # Metadata is one explicit JSON fence. Other code fences cannot impersonate headings.
    metadata = re.search(r'(?m)^```json\s*\n([\s\S]*?)\n```\s*$', content)
    if not metadata:
        raise ValueError('design requires a JSON metadata fence')
    data = strict_json(metadata[1])
    fields(data, ['version', 'kind', 'profile', 'requirements', 'operations', 'decisions', 'references', 'not_applicable'],
           ['version', 'kind', 'profile', 'requirements', 'operations', 'decisions'], 'design')
    if type(data['version']) is not int or data['version'] != 1 or data['kind'] != 'reasons-design':
        raise ValueError('unsupported design version/kind')
    if not isinstance(data['profile'], str) or data['profile'] not in {'behavioral', 'structural', 'editorial', 'exploratory'}:
        raise ValueError('invalid design change profile')
    bodies, current, fence, operation_heads = {}, None, None, set()
    for line in content.splitlines():
        marker = re.match(r'^\s*(`{3,}|~{3,})', line)
        if marker:
            if current: bodies[current].append(line)
            token = marker[1]
            if fence is None: fence = token
            elif token[0] == fence[0] and len(token) >= len(fence): fence = None
            continue
        if fence is not None:
            if current: bodies[current].append(line)
            continue
        heading = re.fullmatch(r'##\s+([A-Za-z]+)\s*', line)
        if heading:
            current = heading[1].lower()
            if current in bodies: raise ValueError('duplicate design section')
            bodies[current] = []
        elif current:
            if current == 'operations':
                op_heading = re.match(r'^###\s+([A-Za-z][A-Za-z0-9_-]*)(?:\s|$)', line)
                if op_heading:
                    if op_heading[1] in operation_heads: raise ValueError('duplicate operation body')
                    operation_heads.add(op_heading[1])
            bodies[current].append(line)
    bodies = {name: '\n'.join(lines).strip() for name, lines in bodies.items()}
    omitted = data.get('not_applicable', {})
    if not isinstance(omitted, dict) or set(omitted) - set(SECTIONS):
        raise ValueError('invalid design not_applicable sections')
    for name in SECTIONS:
        if name in omitted:
            if data['profile'] not in {'editorial', 'exploratory'} or name in {'requirements', 'operations', 'safeguards'}:
                raise ValueError('this design section cannot be omitted')
            text(omitted[name], 'not_applicable reason')
        elif not bodies.get(name) or bodies[name].strip().lower() in {'todo', 'tbd', 'pending', 'reviewed.', '[todo]'}:
            raise ValueError('missing concrete REASONS section: ' + name)
    requirements = ids(data['requirements'], 'design requirements')
    operations = data['operations']
    if not isinstance(operations, list) or not operations or len(operations) > 200:
        raise ValueError('design needs bounded operations')
    ids([o.get('id') for o in operations if isinstance(o, dict)], 'operation IDs')
    if not all(isinstance(o, dict) for o in operations): raise ValueError('invalid operation')
    by_id = {o['id']: o for o in operations}
    for op in operations:
        fields(op, ['id', 'requirements', 'paths', 'depends_on', 'verification'],
               ['id', 'requirements', 'paths', 'depends_on', 'verification'], 'operation')
        if set(ids(op['requirements'], 'operation requirements')) - set(requirements):
            raise ValueError('operation references unknown requirements')
        validate_patterns(op['paths'], 'operation paths')
        if set(ids(op['depends_on'], 'operation dependencies', empty=True)) - set(by_id) or op['id'] in op['depends_on']:
            raise ValueError('invalid operation dependencies')
        text(op['verification'], 'operation verification')
        if op['id'] not in operation_heads:
            raise ValueError('operation has no matching design body: ' + op['id'])
    if set(requirements) - {r for o in operations for r in o['requirements']}:
        raise ValueError('design requirement has no operation')
    visited, active = set(), set()
    def walk(ident):
        if ident in active: raise ValueError('cyclic design operation dependencies')
        if ident in visited: return
        active.add(ident)
        for dep in by_id[ident]['depends_on']: walk(dep)
        active.remove(ident); visited.add(ident)
    for ident in by_id: walk(ident)
    decisions = data['decisions']
    if not isinstance(decisions, list) or len(decisions) > 200: raise ValueError('invalid design decisions')
    ids([d.get('id') for d in decisions if isinstance(d, dict)], 'decision IDs', empty=True)
    for decision in decisions:
        fields(decision, ['id', 'status', 'operations', 'reason'], ['id', 'status', 'operations', 'reason'], 'design decision')
        if not isinstance(decision['status'], str) or decision['status'] not in {'resolved', 'open', 'proposed'}:
            raise ValueError('invalid design decision status')
        if set(ids(decision['operations'], 'decision operations')) - set(by_id): raise ValueError('unknown decision operation')
        text(decision['reason'], 'decision reasoning')
    refs = data.get('references', [])
    if not isinstance(refs, list) or len(refs) > 100: raise ValueError('invalid design references')
    for ref in refs:
        fields(ref, ['path', 'sha256'], ['path', 'sha256'], 'design reference')
        if p.sha(p.local_file(root, ref['path'])) != ref['sha256']: raise ValueError('design referenced contract changed')
    return {**data, 'sections': bodies, 'path': entry['path'], 'sha256': entry['sha256']}


def artifact(root, task, tp, ident):
    if not isinstance(ident, str) or ident not in task['evidence']:
        raise ValueError('missing design/alignment evidence ID')
    entry = task['evidence'][ident]
    evidence.verify_entry(root, entry, tp)
    if entry['type'] != 'artifact': raise ValueError('design/alignment must be artifact evidence')
    return entry


def ready(root, task, tp, design_id, alignment_id):
    entry = artifact(root, task, tp, design_id); design = document(root, entry)
    audit_entry = artifact(root, task, tp, alignment_id)
    audit = p.load(p.local_file(root, audit_entry['path']), LIMIT)
    fields(audit, ['version', 'kind', 'design', 'task_contract', 'operations', 'coverage', 'basis', 'reviewer', 'decision', 'reason', 'completed_dependencies', 'evidence_bindings'],
           ['version', 'kind', 'design', 'task_contract', 'operations', 'coverage', 'basis', 'reviewer', 'decision', 'reason', 'completed_dependencies', 'evidence_bindings'], 'alignment review')
    if type(audit['version']) is not int or audit['version'] != 1 or audit['kind'] != 'reasons-alignment' or audit['decision'] != 'ready':
        raise ValueError('alignment review is not ready')
    if audit['design'] != {'path': entry['path'], 'sha256': entry['sha256']} or audit['task_contract'] != evidence.contract(task):
        raise ValueError('alignment review is stale for design/task contract')
    text(audit['reason'], 'alignment observation')
    fields(audit['reviewer'], ['name', 'type', 'independent'], ['name', 'type', 'independent'], 'alignment reviewer')
    text(audit['reviewer']['name'], 'alignment reviewer')
    if audit['reviewer']['type'] not in ['agent', 'human'] or type(audit['reviewer']['independent']) is not bool:
        raise ValueError('invalid alignment reviewer type/independence')
    selected = ids(audit['operations'], 'selected design operations')
    by_id = {o['id']: o for o in design['operations']}
    if set(selected) - set(by_id): raise ValueError('alignment selects unknown operations')
    completed = audit['completed_dependencies']
    if not isinstance(completed, dict) or set(completed) - set(by_id): raise ValueError('invalid dependency evidence')
    proof_ids = ids(audit['basis'], 'alignment basis')
    if set(proof_ids) & {design_id, alignment_id}: raise ValueError('alignment basis must reference an independent decision/source artifact')
    for ident in proof_ids:
        if ident not in task['evidence']: raise ValueError('alignment basis evidence is missing')
        record = task['evidence'][ident]; evidence.verify_entry(root, record, tp)
        if record['type'] not in {'artifact', 'source'}: raise ValueError('alignment basis must preserve a decision/source')
    expected_ids = set(proof_ids)
    for ident in completed.values():
        if not isinstance(ident, str) or ident not in task['evidence']:
            raise ValueError('dependency evidence is missing')
        expected_ids.add(ident)
    recorded = audit['evidence_bindings']
    current = {ident: p.signature(task['evidence'][ident]) for ident in expected_ids}
    if not isinstance(recorded, dict) or recorded != current:
        raise ValueError('alignment decision/dependency evidence changed after review')
    for op_id in selected:
        for dep in by_id[op_id]['depends_on']:
            if dep not in selected and dep not in completed: raise ValueError('selected operation dependency is not ready')
            if dep in selected and selected.index(dep) >= selected.index(op_id):
                raise ValueError('selected operations violate dependency execution order')
    for dep, ident in completed.items():
        if dep in selected: raise ValueError('selected operations cannot also be completed dependencies')
        if ident not in task['evidence']: raise ValueError('dependency evidence is missing')
        evidence.verify_entry(root, task['evidence'][ident], tp)
    for decision in design['decisions']:
        if set(decision['operations']) & set(selected) and decision['status'] != 'resolved':
            raise ValueError('selected operation has an unresolved design decision: ' + decision['id'])
    coverage = audit['coverage']; criteria = {c['id'] for c in task['acceptance']}
    if not isinstance(coverage, dict) or set(coverage) != criteria: raise ValueError('alignment must cover every task acceptance criterion')
    covered = set()
    for ops in coverage.values():
        if set(ids(ops, 'criterion operations')) - set(selected): raise ValueError('criterion references unselected operations')
        covered.update(ops)
    if covered != set(selected): raise ValueError('selected operation has no acceptance criterion')
    allowed = [pattern for ident in selected for pattern in by_id[ident]['paths']]
    scope = task.get('scope')
    validate_patterns(scope, 'task scope for design alignment')
    for value in scope:
        inside(root, value)
        if any(c in value for c in '*?['):
            permitted = value in allowed
        elif inside(root, value).is_dir():
            permitted = value in allowed or value + '/**' in allowed or '**' in allowed
        else:
            permitted = matches(value, allowed)
        if not permitted: raise ValueError('task scope exceeds selected design operations: ' + value)
    return {'design': design, 'alignment': audit, 'operations': selected}


def bound_id(bound, name):
    values = bound.get(name)
    if not isinstance(values, dict) or len(values) != 1: raise ValueError('missing bound ' + name + ' input')
    return next(iter(values))


def check(root, task, tp, route, bound, *, result_ids=None):
    checks = route.get('entry_checks', []) if result_ids is None else route.get('result_checks', [])
    for role in checks:
        if role == 'design':
            if result_ids is None: ident = bound_id(bound, 'design')
            else:
                candidates = [i for i in result_ids if task['evidence'][i]['type'] == 'artifact' and task['evidence'][i]['path'].endswith('.md')]
                if len(candidates) != 1: raise ValueError('design validation needs exactly one Markdown design artifact')
                ident = candidates[0]
            document(root, artifact(root, task, tp, ident))
        elif role == 'alignment':
            design_id = bound_id(bound, 'design')
            if result_ids is None: alignment_id = bound_id(bound, 'alignment')
            else:
                candidates = [i for i in result_ids if task['evidence'][i]['type'] == 'artifact' and task['evidence'][i]['path'].endswith('.json')]
                if len(candidates) != 1: raise ValueError('alignment validation needs exactly one alignment JSON artifact')
                alignment_id = candidates[0]
            ready(root, task, tp, design_id, alignment_id)


def selected_document(root, task, tp, bound):
    if 'design' not in bound: return None
    ident = bound_id(bound, 'design'); design = document(root, artifact(root, task, tp, ident))
    selected = [o['id'] for o in design['operations']]
    if 'alignment' in bound:
        selected = ready(root, task, tp, ident, bound_id(bound, 'alignment'))['operations']
    by_id = {o['id'] for o in design['operations']}
    blocks, prefix, current, fence = {}, [], None, None
    for line in design['sections']['operations'].splitlines():
        marker = re.match(r'^\s*(`{3,}|~{3,})', line)
        heading = re.match(r'^###\s+([A-Za-z][A-Za-z0-9_-]*)(?:\s|$)', line) if fence is None else None
        if heading and heading[1] in by_id:
            current = heading[1]; blocks[current] = []
        (blocks[current] if current else prefix).append(line)
        if marker:
            token = marker[1]
            if fence is None: fence = token
            elif token[0] == fence[0] and len(token) >= len(fence): fence = None
    operations = '\n'.join(prefix) + '\n' + '\n\n'.join('\n'.join(blocks[ident]) for ident in selected)
    content = '\n\n'.join('## ' + name.title() + '\n' + (operations.strip() if name == 'operations' else design['sections'].get(name, 'Not applicable: ' + design.get('not_applicable', {}).get(name, '')))
                            for name in SECTIONS)
    return {'path': design['path'], 'content_scope': 'reasons_selected_operations', 'selected_operations': selected,
            'reasons': ['bound design; common contract sections and selected operations only'], 'content': content}


def alignment_template(root, task, tp, design_id, operations, output, basis=()):
    from .core import runtime_path
    entry = artifact(root, task, tp, design_id); design = document(root, entry)
    ids(operations, 'selected design operations')
    if set(operations) - {o['id'] for o in design['operations']}:
        raise ValueError('template selects unknown design operations')
    path = runtime_path(root, output)
    if path.exists(): raise ValueError('alignment template already exists; review it explicitly')
    for ident in basis:
        if ident not in task['evidence']: raise ValueError('template basis is missing')
        evidence.verify_entry(root, task['evidence'][ident], tp)
    template = {'version': 1, 'kind': 'reasons-alignment', 'design': {'path': entry['path'], 'sha256': entry['sha256']},
                'task_contract': evidence.contract(task), 'operations': operations,
                'coverage': {c['id']: operations for c in task['acceptance']}, 'basis': list(basis),
                'evidence_bindings': {ident: p.signature(task['evidence'][ident]) for ident in basis},
                'reviewer': {'name': '', 'type': 'agent', 'independent': False}, 'decision': 'pending',
                'reason': '', 'completed_dependencies': {}}
    p.atomic(path, template)
    return {'status': 'prepared', 'path': output, 'note': 'Pending template only. Review actual intent, scope, decisions and coverage before recording ready; no new user approval is implied.'}
