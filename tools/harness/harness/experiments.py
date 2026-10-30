"""Small local experiments: explicit protocols, bounded trials and fair comparison."""
from __future__ import annotations

import math
from pathlib import Path
import statistics
import sys
import time
import uuid

from . import provenance as p
from .core import inside, matches, runtime_path
from .processes import execute


def number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def validate(root: Path, protocol: dict, *, check_inputs=True) -> None:
    if not isinstance(protocol, dict) or protocol.get('version') != 1:
        raise ValueError('unsupported experiment protocol')
    for key in ('question', 'population', 'limitations'):
        if not isinstance(protocol.get(key), str) or not protocol[key].strip():
            raise ValueError('protocol needs ' + key)
    if protocol.get('evaluation_type') not in {'fixture', 'author_pilot', 'agent_benchmark'}:
        raise ValueError('declare fixture, author_pilot or agent_benchmark explicitly')
    if not isinstance(protocol.get('inputs'), list) or not protocol['inputs']:
        raise ValueError('declare at least one fixed input file')
    for relative in protocol['inputs']:
        if not isinstance(relative, str) or not relative:
            raise ValueError('input paths must be nonempty relative strings')
        inside(root, relative)
        if check_inputs:
            p.local_file(root, relative)
    seeds = protocol.get('seeds')
    if (not isinstance(seeds, list) or not 1 <= len(seeds) <= 20
            or any(type(seed) is not int for seed in seeds) or len(set(seeds)) != len(seeds)):
        raise ValueError('declare 1..20 distinct integer seeds before execution')
    for key, ceiling in [('timeout', 3600), ('budget_seconds', 7200), ('max_output_bytes', 64 * 1024 * 1024)]:
        value = protocol.get(key, 4 * 1024 * 1024 if key == 'max_output_bytes' else None)
        if not number(value) or not 0 < value <= ceiling or (key == 'max_output_bytes' and type(value) is not int):
            raise ValueError('invalid protocol budget: ' + key)
    metrics = protocol.get('metrics')
    if not isinstance(metrics, dict) or not metrics:
        raise ValueError('declare metrics, units, direction and quality limits')
    for name, metric in metrics.items():
        if (not isinstance(metric, dict) or metric.get('direction') not in {'minimize', 'maximize'}
                or not isinstance(metric.get('unit'), str) or not metric['unit'].strip()):
            raise ValueError('invalid metric contract: ' + name)
        for bound in ('minimum', 'maximum'):
            if bound in metric and not number(metric[bound]):
                raise ValueError('metric limits must be finite numbers')
        if metric.get('minimum', -math.inf) > metric.get('maximum', math.inf):
            raise ValueError('contradictory metric limits')
    variants = protocol.get('variants')
    if not isinstance(variants, dict) or len(variants) < 2:
        raise ValueError('declare a baseline and at least one candidate')
    if protocol.get('baseline') not in variants:
        raise ValueError('baseline must name a declared variant')
    for name, variant in variants.items():
        if not isinstance(variant, dict) or not isinstance(variant.get('command'), list) or not variant['command']:
            raise ValueError('variant needs an argv command: ' + name)
        if not all(isinstance(arg, str) and arg for arg in variant['command']):
            raise ValueError('command arguments must be strings')
        if not any('{metrics}' in arg for arg in variant['command']):
            raise ValueError('command must produce a fresh {metrics} file')
        if not isinstance(variant.get('parameters'), dict):
            raise ValueError('variant needs explicit parameters')
        if not isinstance(variant.get('source_paths', []), list) or any(
                not isinstance(x, str) or not x or x.startswith('/') or '..' in x.split('/')
                for x in variant.get('source_paths', [])):
            raise ValueError('variant source_paths must be repository-relative patterns')


def parse_metrics(path: Path, contract: dict) -> dict:
    data = p.load(path, 1024 * 1024)
    metrics = data.get('metrics') if isinstance(data, dict) else None
    if not isinstance(metrics, dict) or set(metrics) != set(contract):
        raise ValueError('fresh metrics must contain exactly the declared metric names')
    result = {}
    for name, spec in contract.items():
        item = metrics[name]
        if (not isinstance(item, dict) or item.get('unit') != spec['unit'] or not number(item.get('value'))):
            raise ValueError('metric value must be finite and use the declared unit: ' + name)
        result[name] = item['value']
    return result


def run(root: Path, recipe: str, variant: str) -> dict:
    root = root.resolve()
    recipe_path = p.local_file(root, recipe)
    protocol = p.load(recipe_path)
    validate(root, protocol)
    if variant not in protocol['variants']:
        raise ValueError('unknown variant')
    spec = protocol['variants'][variant]
    before = p.snapshot(root)
    before_executable = p.executable_snapshot(root)
    directory = runtime_path(root, '.runtime/experiments/' + uuid.uuid4().hex)
    directory.mkdir(parents=True, mode=0o700)
    started = time.monotonic()
    trials = []
    for index, seed in enumerate(protocol['seeds']):
        remaining = protocol['budget_seconds'] - (time.monotonic() - started)
        trial = {'trial': index, 'seed': seed, 'status': 'not_run', 'metrics': {}, 'artifacts': {}}
        if remaining <= 0:
            trial['error'] = 'total_budget_exhausted'
            trials.append(trial)
            continue
        folder = directory / str(index)
        folder.mkdir(mode=0o700)
        metrics_path, log = folder / 'metrics.json', folder / 'output.log'
        substitutions = {'{python}': sys.executable, '{metrics}': str(metrics_path),
                         '{output_dir}': str(folder), '{seed}': str(seed), '{trial}': str(index)}
        command = []
        for arg in spec['command']:
            for key, value in substitutions.items():
                arg = arg.replace(key, value)
            command.append(arg)
        execution = execute(command, cwd=root, log=log, timeout=min(protocol['timeout'], remaining),
                            max_output_bytes=protocol.get('max_output_bytes', 4 * 1024 * 1024))
        trial.update(execution=execution, command=command, cwd='.', status='failed')
        trial['artifacts'][log.relative_to(root).as_posix()] = p.sha(log)
        try:
            if execution['error'] or execution['exit_code'] != 0:
                raise ValueError(execution['error'] or 'nonzero_exit')
            p.local_file(root, metrics_path.relative_to(root).as_posix())
            metrics = parse_metrics(metrics_path, protocol['metrics'])
            trial['metrics'] = metrics
            trial['artifacts'][metrics_path.relative_to(root).as_posix()] = p.sha(metrics_path)
            for name, value in metrics.items():
                limits = protocol['metrics'][name]
                if value < limits.get('minimum', -math.inf) or value > limits.get('maximum', math.inf):
                    raise ValueError('quality_limit: ' + name)
            trial['status'] = 'passed'
        except (OSError, ValueError, TypeError) as exc:
            trial['error'] = str(exc)
        trials.append(trial)
    status = 'passed' if all(t['status'] == 'passed' for t in trials) else 'failed'
    if p.snapshot(root) != before or p.executable_snapshot(root) != before_executable:
        status = 'stale'
    report = {'version': 1, 'record_type': 'experiment_run', 'created_at': p.now(), 'status': status,
              'protocol': protocol, 'protocol_digest': p.signature(protocol), 'recipe': recipe,
              'variant': variant, 'source_snapshot': before, 'environment': p.environment(),
              'source_executable': before_executable,
              'workspace': str(root),
              'inputs': {name: p.sha(p.local_file(root, name)) for name in protocol['inputs']},
              'trials': trials, 'summary': summarize(trials, protocol['metrics']),
              'product_accepted': False}
    path = directory / 'report.json'
    p.atomic(path, report)
    return {**report, 'report': path.relative_to(root).as_posix()}


def summarize(trials: list[dict], metrics: dict) -> dict:
    result = {'attempted': len(trials), 'passed': sum(t['status'] == 'passed' for t in trials),
              'failed': sum(t['status'] == 'failed' for t in trials),
              'not_run': sum(t['status'] == 'not_run' for t in trials), 'metrics': {}}
    for name in metrics:
        values = [t['metrics'][name] for t in trials if t['status'] == 'passed']
        if values:
            result['metrics'][name] = {'count': len(values), 'mean': statistics.mean(values),
                                       'median': statistics.median(values), 'minimum': min(values), 'maximum': max(values)}
    return result


def verify_report(root: Path, report: dict, *, task_path: Path | None = None, require_current=False) -> None:
    try:
        _verify_report(root, report, task_path=task_path, require_current=require_current)
    except (KeyError, TypeError, AttributeError, IndexError):
        raise ValueError('invalid experiment report structure') from None


def _verify_report(root: Path, report: dict, *, task_path: Path | None = None, require_current=False) -> None:
    if not isinstance(report, dict) or report.get('record_type') != 'experiment_run' or report.get('version') != 1 or report.get('status') != 'passed':
        raise ValueError('experiment evidence needs a passing run')
    protocol = report['protocol']
    validate(root, protocol, check_inputs=require_current)
    if p.signature(protocol) != report['protocol_digest'] or report['variant'] not in protocol['variants']:
        raise ValueError('experiment protocol binding changed')
    trials = report['trials']
    if (len(trials) != len(protocol['seeds']) or [t['seed'] for t in trials] != protocol['seeds']
            or any(t['status'] != 'passed' or t['execution'].get('error') is not None
                   or type(t['execution'].get('exit_code')) is not int or t['execution']['exit_code'] != 0
                   or type(t['seed']) is not int for t in trials)):
        raise ValueError('experiment has failed, missing or reordered trials')
    if (not isinstance(report.get('inputs'), dict) or set(report['inputs']) != set(protocol['inputs'])
            or any(not isinstance(value, str) or len(value) != 64
                   or any(char not in '0123456789abcdef' for char in value) for value in report['inputs'].values())):
        raise ValueError('experiment input bindings are missing or invalid')
    seen_artifacts, run_folder = set(), None
    for index, trial in enumerate(trials):
        if type(trial.get('trial')) is not int or trial['trial'] != index:
            raise ValueError('experiment trial indices must match the declared order')
        if not trial['artifacts']:
            raise ValueError('experiment has no raw artifacts')
        metrics_files = [name for name in trial['artifacts'] if name.endswith('/metrics.json')]
        if len(metrics_files) != 1:
            raise ValueError('experiment needs one fresh metrics file per trial')
        folder = Path(metrics_files[0]).parent
        if (folder.name != str(index) or len(folder.parts) != 4 or folder.parts[:2] != ('.runtime', 'experiments')
                or (folder / 'output.log').as_posix() not in trial['artifacts']
                or seen_artifacts.intersection(trial['artifacts'])):
            raise ValueError('experiment trials need distinct metrics/log artifacts in their own directories')
        if run_folder is not None and folder.parent != run_folder:
            raise ValueError('experiment trials belong to different runs')
        run_folder = folder.parent
        seen_artifacts.update(trial['artifacts'])
        workspace = report.get('workspace')
        interpreter = report.get('environment', {}).get('python_executable')
        if not isinstance(workspace, str) or not isinstance(interpreter, str):
            raise ValueError('experiment command has no workspace/interpreter binding')
        output_dir = Path(workspace) / folder
        substitutions = {'{python}': interpreter, '{metrics}': str(output_dir / 'metrics.json'),
                         '{output_dir}': str(output_dir), '{seed}': str(trial['seed']), '{trial}': str(index)}
        expected = []
        for arg in protocol['variants'][report['variant']]['command']:
            for key, value in substitutions.items():
                arg = arg.replace(key, value)
            expected.append(arg)
        if trial.get('command') != expected or trial.get('cwd') != '.':
            raise ValueError('experiment command disagrees with its declared variant/trial')
        for relative, digest in trial['artifacts'].items():
            if p.sha(p.local_file(root, relative)) != digest:
                raise ValueError('experiment raw artifact changed')
        if len(metrics_files) != 1 or parse_metrics(p.local_file(root, metrics_files[0]), protocol['metrics']) != trial['metrics']:
            raise ValueError('experiment metric values disagree with raw artifact')
        for name, value in trial['metrics'].items():
            spec = protocol['metrics'][name]
            if value < spec.get('minimum', -math.inf) or value > spec.get('maximum', math.inf):
                raise ValueError('experiment quality limit not met')
    if report['summary'] != summarize(trials, protocol['metrics']):
        raise ValueError('experiment aggregate changed')
    if require_current:
        from .evidence import current_sources
        current_sources(root, report, task_path)
        if report['inputs'] != {name: p.sha(p.local_file(root, name)) for name in protocol['inputs']}:
            raise ValueError('experiment inputs changed')


def compare(root: Path, baseline: str, candidate: str) -> dict:
    root = root.resolve()
    left, right = [p.load(p.local_file(root, name)) for name in (baseline, candidate)]
    for report in (left, right):
        verify_report(root, report)
    if (left['protocol_digest'] != right['protocol_digest'] or left['inputs'] != right['inputs']
            or left['environment'] != right['environment'] or left['variant'] != left['protocol']['baseline']
            or right['variant'] == left['variant']):
        raise ValueError('incompatible experiment conditions or baseline/candidate ordering')
    protocol = left['protocol']
    sources = set(left['source_snapshot']) | set(right['source_snapshot'])
    changed = [name for name in sorted(sources)
               if (left['source_snapshot'].get(name) != right['source_snapshot'].get(name)
                   or left.get('source_executable', {}).get(name) != right.get('source_executable', {}).get(name))]
    allowed = protocol['variants'][left['variant']].get('source_paths', []) + protocol['variants'][right['variant']].get('source_paths', [])
    if any(not matches(name, allowed) for name in changed):
        raise ValueError('source changed outside the predeclared variant source_paths')
    deltas = {}
    for name, spec in protocol['metrics'].items():
        a, b = [report['summary']['metrics'][name]['mean'] for report in (left, right)]
        deltas[name] = {'baseline_mean': a, 'candidate_mean': b, 'delta': b - a,
                        'improvement': (b - a) * (1 if spec['direction'] == 'maximize' else -1), 'unit': spec['unit']}
    record = {'status': 'passed', 'record_type': 'experiment_comparison', 'created_at': p.now(),
              'baseline': {'path': baseline, 'sha256': p.sha(p.local_file(root, baseline))},
              'candidate': {'path': candidate, 'sha256': p.sha(p.local_file(root, candidate))},
              'evaluation_type': protocol['evaluation_type'], 'metrics': deltas,
              'changed_sources': changed, 'product_accepted': False,
              'note': 'Descriptive comparison only; no statistical significance, agent quality or cost-saving claim is inferred.'}
    output = root / '.runtime/experiments/comparisons' / (uuid.uuid4().hex + '.json')
    p.atomic(output, record)
    return {**record, 'report': output.relative_to(root).as_posix()}
