"""CLI surface for explicit, bounded skill-route state updates."""
from . import flow_catalog, skill_flows, reasons


def configure(commands):
    parser = commands.add_parser('flow', help='Control skill-route calls, returns and guarded transitions; no automatic work execution')
    actions = parser.add_subparsers(dest='flow_action', required=True)
    p = actions.add_parser('catalog'); p.add_argument('--node')
    for action in ['ready', 'alignment-template']:
        p = actions.add_parser(action); p.add_argument('--task', required=True); p.add_argument('--design', required=True)
        if action == 'ready': p.add_argument('--alignment', required=True)
        else:
            p.add_argument('--operation', action='append', required=True); p.add_argument('--output', required=True)
            p.add_argument('--basis', action='append', default=[])
    p = actions.add_parser('start'); p.add_argument('run')
    p.add_argument('--task', required=True); p.add_argument('--node', required=True)
    p.add_argument('--input', action='append', default=[], metavar='NAME=EVIDENCE_ID')
    for name, default in [('moves', 100), ('depth', 8), ('visits', 3)]:
        p.add_argument('--max-' + name, type=int, default=default)
    for name in ['status', 'context', 'step', 'validate', 'move', 'ask', 'answer', 'finish', 'restart', 'block']:
        p = actions.add_parser(name); p.add_argument('run')
        if name == 'context':
            p.add_argument('--read', action='store_true'); p.add_argument('--project')
        elif name != 'status':
            p.add_argument('--expect-revision', type=int)
        if name == 'step': p.add_argument('step')
        if name in ['step', 'validate', 'answer']:
            p.add_argument('--evidence', action='append', required=True)
        if name == 'validate': p.add_argument('--result', choices=['passed', 'failed', 'blocked'], required=True)
        if name in ['validate', 'answer', 'restart', 'block']:
            p.add_argument('--reason', required=True)
        if name == 'move':
            p.add_argument('edge'); p.add_argument('--reason')
        if name in ['move', 'restart']:
            p.add_argument('--input', action='append', default=[], metavar='NAME=EVIDENCE_ID')
        if name == 'restart': p.add_argument('--node')
        if name == 'ask': p.add_argument('--question', required=True)
        if name == 'answer':
            p.add_argument('--question-id', required=True); p.add_argument('--choice', required=True)


def inputs(values):
    bindings = {}
    for value in values:
        name, separator, ident = value.partition('=')
        if not separator or not name or not ident or name in bindings:
            raise ValueError('route inputs need unique NAME=EVIDENCE_ID bindings')
        bindings[name] = ident
    return bindings


def execute(root, args):
    action = args.flow_action
    if action == 'catalog':
        catalog = flow_catalog.load(root)
        if args.node:
            if args.node not in catalog['nodes']: raise ValueError('unknown flow node')
            return {'status': 'passed', 'node': catalog['nodes'][args.node], 'outgoing': flow_catalog.outgoing(catalog, args.node)}
        return {'status': 'passed', 'skills': len({n['skill'] for n in catalog['nodes'].values()}),
                'nodes': [{'id': key, 'when': value['when']} for key, value in catalog['nodes'].items()],
                'edge_count': len(catalog['edges']), 'digest': catalog['digest']}
    if action in ['ready', 'alignment-template']:
        tp, task = skill_flows.task_data(root, args.task)
        if action == 'alignment-template':
            return reasons.alignment_template(root, task, tp, args.design, args.operation, args.output, args.basis)
        result = reasons.ready(root, task, tp, args.design, args.alignment)
        return {'status': 'passed', 'task': args.task, 'profile': result['design']['profile'], 'operations': result['operations'],
                'note': 'Bound design/review readiness checked; semantic alignment and user authorship are reviewer judgments.'}
    if action == 'start':
        return skill_flows.start(root, args.run, args.task, args.node, inputs=inputs(args.input),
                                max_moves=args.max_moves, max_depth=args.max_depth, max_visits=args.max_visits)
    if action == 'status': return skill_flows.inspect(root, args.run)
    if action == 'context': return skill_flows.selected_context(root, args.run, read_contents=args.read, workflow=args.project)
    kwargs = {'expect_revision': args.expect_revision}
    for option in ['step', 'result', 'reason', 'question', 'question_id', 'choice', 'node']:
        if hasattr(args, option): kwargs[option] = getattr(args, option)
    if hasattr(args, 'edge'): kwargs['edge_id'] = args.edge
    if hasattr(args, 'evidence'): kwargs['evidence_ids'] = args.evidence
    if hasattr(args, 'input'): kwargs['inputs'] = inputs(args.input)
    return skill_flows.act(root, args.run, action, **kwargs)
