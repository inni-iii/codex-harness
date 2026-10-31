"""Declarative skill routes and allowed edges; no code, shell or expression eval."""
from __future__ import annotations

from pathlib import Path
import re
import tomllib

from .core import inside
from .provenance import local_file, sha, signature
from .workflows import documents
from .reasons import CHECKS

CATALOG = '.agents/skill-flow.toml'
SLUG = r'[a-z0-9]+(?:-[a-z0-9]+)*'
NODE = re.compile(SLUG + ':' + SLUG)
EVIDENCE_TYPES = {'artifact', 'source', 'check', 'experiment'}


def text(value, label):
    if not isinstance(value, str) or not value.strip() or len(value) > 2000:
        raise ValueError(f'{label} needs nonempty text of at most 2000 characters')
    return value


def names(values, label, *, nonempty=False):
    if (not isinstance(values, list) or (nonempty and not values)
            or not all(isinstance(x, str) and re.fullmatch(SLUG, x) for x in values)
            or len(set(values)) != len(values)):
        raise ValueError(f'invalid {label}')
    return values


def fields(value, allowed, required, label):
    if not isinstance(value, dict) or set(value) - set(allowed) or set(required) - set(value):
        raise ValueError(f'invalid {label} fields')


def read_toml(root, relative):
    path = local_file(root, relative)
    if path.stat().st_size > 1024 * 1024:
        raise ValueError('flow catalog exceeds size limit')
    return tomllib.loads(path.read_text())


def load(root: Path) -> dict:
    graph = read_toml(root, CATALOG)
    fields(graph, ['version', 'edges'], ['version', 'edges'], 'flow graph')
    if type(graph['version']) is not int or graph['version'] != 1 or not isinstance(graph['edges'], list):
        raise ValueError('flow graph requires version 1 and edges')
    nodes, sources = {}, {CATALOG: graph}
    skills = sorted(p for p in (root / '.agents/skills').iterdir() if p.is_dir())
    for folder in skills:
        relative = f'.agents/skills/{folder.name}/routes.toml'
        data = read_toml(root, relative)
        sources[relative] = data
        fields(data, ['version', 'routes'], ['version', 'routes'], 'skill routes')
        if type(data['version']) is not int or data['version'] != 1 or not isinstance(data['routes'], list) or not data['routes']:
            raise ValueError('each skill needs version 1 and at least one route')
        for route in data['routes']:
            fields(route, ['name', 'when', 'kind', 'inputs', 'documents', 'steps', 'validation',
                           'evidence_types', 'required_calls', 'finish', 'entry_checks', 'result_checks'],
                   ['name', 'when', 'kind', 'inputs', 'documents', 'steps', 'validation', 'evidence_types', 'required_calls', 'finish'], 'route')
            names([route['name']], 'route name')
            ident = f'{folder.name}:{route["name"]}'
            if ident in nodes:
                raise ValueError('duplicate flow node')
            text(route['when'], 'route selection')
            if not isinstance(route['kind'], str) or route['kind'] not in {'plan', 'research', 'experiment', 'design', 'implement', 'debug', 'review'}:
                raise ValueError('invalid route kind')
            for phase in ['entry_checks', 'result_checks']:
                checks = route.get(phase, [])
                if (not isinstance(checks, list) or not all(isinstance(c, str) and c in CHECKS for c in checks)
                        or len(set(checks)) != len(checks)):
                    raise ValueError('invalid route design checks')
            if ('design' in route.get('entry_checks', []) or 'alignment' in route.get('entry_checks', [])
                    or 'alignment' in route.get('result_checks', [])) and 'design' not in route['inputs']:
                raise ValueError('design check needs a required design input')
            if 'alignment' in route.get('entry_checks', []) and 'alignment' not in route['inputs']:
                raise ValueError('alignment check needs a required alignment input')
            names(route['inputs'], 'route inputs', nonempty=True)
            if 'request' not in route['inputs']:
                raise ValueError('routes must bind the task request')
            documents(root, route['documents'], 'route documents')
            for doc in route['documents']:
                if not inside(root, doc).is_relative_to(folder.resolve()):
                    raise ValueError('route procedures belong to their owning skill')
                local_file(root, doc)
            steps = route['steps']
            if not isinstance(steps, list) or not steps:
                raise ValueError('route needs ordered steps')
            for step in steps:
                fields(step, ['id', 'instruction'], ['id', 'instruction'], 'route step')
                text(step['instruction'], 'step instruction')
            names([s['id'] for s in steps], 'step IDs', nonempty=True)
            text(route['validation'], 'route validation')
            types = route['evidence_types']
            if (not isinstance(types, list) or not types or not all(isinstance(t, str) and t in EVIDENCE_TYPES for t in types)
                    or len(set(types)) != len(types)):
                raise ValueError('invalid required evidence types')
            calls = route['required_calls']
            if (not isinstance(calls, list) or not all(isinstance(n, str) and NODE.fullmatch(n) for n in calls)
                    or len(set(calls)) != len(calls)):
                raise ValueError('invalid required calls')
            if not isinstance(route['finish'], bool):
                raise ValueError('finish must be boolean')
            entrypoint = f'.agents/skills/{folder.name}/SKILL.md'
            for doc in [entrypoint, *route['documents']]:
                sources[doc] = sha(local_file(root, doc))
            nodes[ident] = {**route, 'skill': folder.name, 'entrypoint': f'.agents/skills/{folder.name}/SKILL.md'}
    if len(nodes) > 500 or len(graph['edges']) > 3000:
        raise ValueError('flow graph exceeds node/edge limits')
    edges = {}
    for edge in graph['edges']:
        fields(edge, ['id', 'from', 'to', 'mode', 'when', 'guards', 'choice'],
               ['id', 'from', 'to', 'mode', 'when', 'guards'], 'edge')
        names([edge['id']], 'edge ID')
        if edge['id'] in edges or not all(isinstance(edge[k], str) and edge[k] in nodes for k in ['from', 'to']):
            raise ValueError('duplicate edge or unknown endpoint')
        if not all(isinstance(edge[k], str) for k in ['mode', 'when']) or edge['mode'] not in {'call', 'transition'} or edge['when'] not in {'steps_complete', 'user_choice', 'reason'}:
            raise ValueError('invalid edge mode/condition')
        guards = edge['guards']
        if (not isinstance(guards, list) or not all(isinstance(g, str) and g in {'validated', 'failed'} for g in guards)
                or len(set(guards)) != len(guards) or set(guards) == {'validated', 'failed'}):
            raise ValueError('invalid edge guards')
        if edge['mode'] == 'transition' and not guards:
            raise ValueError('transitions require validated or failed guard')
        if edge['mode'] == 'call' and edge['from'] == edge['to']:
            raise ValueError('direct recursive calls are unsupported')
        if edge['when'] == 'user_choice':
            names([edge.get('choice')], 'edge choice')
        elif 'choice' in edge:
            raise ValueError('choice belongs only to user_choice edges')
        edges[edge['id']] = edge
    for ident, route in nodes.items():
        for target in route['required_calls']:
            if not any(e['from'] == ident and e['to'] == target and e['mode'] == 'call' for e in edges.values()):
                raise ValueError('required call has no registered edge: ' + ident)
        if not route['finish'] and not any(e['from'] == ident and e['mode'] == 'transition' and 'validated' in e['guards'] for e in edges.values()):
            raise ValueError('nonterminal route has no successful continuation: ' + ident)
        choices = [e['choice'] for e in edges.values() if e['from'] == ident and e['when'] == 'user_choice']
        if len(set(choices)) != len(choices):
            raise ValueError('user choices must be unique at each node')
    return {'nodes': nodes, 'edges': edges, 'digest': signature(sources)}


def outgoing(catalog, node):
    return [e for e in catalog['edges'].values() if e['from'] == node]
