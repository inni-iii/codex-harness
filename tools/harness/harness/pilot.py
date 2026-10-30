"""Reproducible, scripted workflow pilot; never an agent-quality benchmark."""
from __future__ import annotations

from pathlib import Path
import uuid

from . import checks, evidence, evaluation, experiments, provenance as p, tasks


def run(repository: Path) -> dict:
    root = repository.resolve() / '.runtime/pilots' / uuid.uuid4().hex
    root.mkdir(parents=True, mode=0o700)
    (root / 'tools/harness').mkdir(parents=True)
    (root / 'tools/harness/harness.toml').write_text('''version=1
[[checks]]
id="storage-regression"
command=["{python}","-m","unittest","test_store","-v"]
paths=["**"]
test_summary="unittest"
timeout=10
''')
    observations = []

    def new(slug, kind, goal, acceptance):
        tasks.create(root, slug, kind, goal, [acceptance])

    def attach(slug, ident, kind, path, description, **kwargs):
        evidence.add(root, slug, ident, kind, path, 'A1', description, description, **kwargs)

    def close(slug, reason, findings=None):
        from .completion_review import template
        review = evidence.review_template(root, slug)['review']
        data = p.load(root / review)
        task = p.load(root / 'docs/tasks' / slug / 'task.json')
        data.update(reviewer='Scripted fixture reviewer', independent=False,
                    limitations=['Known-answer replay, authored and reviewed together; no independent agent-quality assessment.'])
        data['criteria'][0].update(decision='passed', reason=reason)
        audit = template(task['kind'])
        audit['scope'] = task['goal']
        for area in audit['areas']:
            area.update(result='checked', reason=reason)
        audit['findings'] = findings or []
        audit['rounds'][0].update(outcome='no_new_findings', reason=reason, evidence=list(task['evidence']))
        if findings:
            ids = [f['id'] for f in findings]
            audit['rounds'][0].update(outcome='new_findings', new_findings=ids,
                                      reason='The missing-key contract failed in the pre-fix run.', evidence=['RED'])
            audit['rounds'].append({'id': 'R2', 'new_findings': [], 'closed_findings': ids,
                                    'outcome': 'no_new_findings', 'reason': reason, 'evidence': ['C1', 'D1']})
        data['verification'] = audit
        p.atomic(root / review, data)
        result = evidence.finish(root, slug, review=review, complete=True)
        if result['status'] != 'passed':
            raise ValueError('pilot closure failed: ' + repr(result))

    new('research', 'research', 'Determine the timeout contract of subprocess.run',
        'Distinguish direct-child timeout from descendant cleanup and record the scope limit')
    (root / 'source.md').write_text('''# Primary-source reading note
URL: https://docs.python.org/3.12/library/subprocess.html
Accessed: 2026-10-31. Python 3.12 documentation.
The run timeout contract kills and waits for its child. Popen exposes start_new_session on POSIX.
This does not state that arbitrary detached descendants are a security sandbox.
No full documentation body is copied. This authored reading note is not a live protocol probe.
''')
    (root / 'research-result.md').write_text('''# Conclusion
Use a bounded pipe reader and process-group cleanup for ordinary local descendants.
Do not infer all-descendant cleanup from a root timeout. Signal-denied environments must fail closed.
Detached sessions and Windows need separate verification. A source note does not prove runtime cleanup.
''')
    attach('research', 'S1', 'source', 'source.md', 'Replay the authored source note; no new live fetch',
           origin='https://docs.python.org/3.12/library/subprocess.html', accessed_at='2026-10-31')
    attach('research', 'R1', 'artifact', 'research-result.md', 'Separate documented guarantees from deployment assumptions')
    close('research', 'The conclusion distinguishes the documented child process contract, ordinary groups, and unverified descendants.')

    new('design', 'design', 'Design an offline persistent item store',
        'Define persistence, invalid/missing input behavior and a reproducible verification plan')
    (root / 'design.md').write_text('''# Local item store contract
Goal: write an item and retrieve it after reopening SQLite.
create(database, key, value) accepts nonempty strings; invalid values raise ValueError.
read(database, key) returns the saved value; missing keys raise KeyError.
Use one small module and context-managed sqlite3 connections. No web API or user identity exists here.
Quality scenario: a new connection reads the same value from the same local database path.
Tests use temporary databases; invalid and absent values are separate cases.
No service latency, multiuser permission, browser E2E or crash durability is claimed.
The tradeoff is a small synchronous fixture rather than an unrequested async/server framework.
''')
    attach('design', 'D1', 'artifact', 'design.md', 'Review concrete interfaces, failure cases, quality scenario and scope limits')
    close('design', 'The persistence and error contracts are observable and testable; unimplemented service guarantees are explicitly excluded.')

    new('implement', 'implement', 'Implement SQLite write and reopen/read',
        'A valid value persists across connections and invalid input is rejected')
    source = '''import sqlite3
def create(database, key, value):
    if not isinstance(key,str) or not key or not isinstance(value,str) or not value:
        raise ValueError('nonempty strings required')
    with sqlite3.connect(database) as connection:
        connection.execute('CREATE TABLE IF NOT EXISTS items (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
        connection.execute('INSERT INTO items VALUES (?,?)', (key,value))
def read(database, key):
    with sqlite3.connect(database) as connection:
        row=connection.execute('SELECT value FROM items WHERE key=?', (key,)).fetchone()
    return row[0]
'''
    test_source = '''import tempfile, unittest
from pathlib import Path
import store
class Storage(unittest.TestCase):
    def test_persistence(self):
        with tempfile.TemporaryDirectory() as directory:
            database=Path(directory)/'items.db'
            store.create(database,'item','saved')
            self.assertEqual(store.read(database,'item'),'saved')
    def test_invalid_input(self):
        with self.assertRaises(ValueError): store.create(':memory:','', 'value')
'''
    (root / 'store.py').write_text(source)
    (root / 'test_store.py').write_text(test_source)
    report = checks.run(root, ['store.py', 'test_store.py'])
    attach('implement', 'C1', 'check', Path(report['report']).relative_to(root).as_posix(),
           'Run real SQLite persistence and invalid-input tests', check='storage-regression')
    close('implement', 'Two executed tests verify the declared write/read and invalid-input subset; the separate missing-key contract remains for debug.')

    new('debug', 'debug', 'Fix the missing-key contract', 'Missing keys raise KeyError while persistence and invalid-input behavior remain valid')
    (root / 'test_store.py').write_text(test_source + '''    def test_missing_key(self):
        with tempfile.TemporaryDirectory() as directory:
            database=Path(directory)/'items.db'
            store.create(database,'existing','saved')
            with self.assertRaises(KeyError): store.read(database,'missing')
''')
    red = checks.run(root, ['store.py', 'test_store.py'])
    if red['status'] != 'failed':
        raise ValueError('pilot bug must reproduce before correction')
    task_path = root / 'docs/tasks/debug/task.json'
    task = p.load(task_path)
    task['findings'] = ['F1']
    p.atomic(task_path, task)
    (root / 'debug-analysis.md').write_text('''# Reproduction and cause
The missing-key test fails with TypeError because fetchone returns None and read indexes it.
Keep the saved-value path and SQL parameters unchanged; raise KeyError before indexing an absent row.
The original failing report is retained in .runtime/checks; the passing report covers all three tests.
''')
    (root / 'store.py').write_text(source.replace('    return row[0]', '    if row is None: raise KeyError(key)\n    return row[0]'))
    green = checks.run(root, ['store.py', 'test_store.py'])
    attach('debug', 'C1', 'check', Path(green['report']).relative_to(root).as_posix(), 'Run all three storage regressions after the narrow fix', check='storage-regression')
    attach('debug', 'D1', 'artifact', 'debug-analysis.md', 'Explain the observed failure and the unchanged surrounding behavior')
    attach('debug', 'RED', 'artifact', Path(red['report']).relative_to(root).as_posix(), 'Keep the observed pre-fix failing regression run')
    finding = {'id': 'F1', 'summary': 'Missing keys raise TypeError instead of KeyError',
               'cause': 'read indexes fetchone() without checking for an absent row', 'status': 'fixed',
               'regression': {'mode': 'automated', 'test_path': 'test_store.py', 'test_id': 'Storage.test_missing_key',
                              'sha256': p.sha(root / 'test_store.py'), 'check': 'storage-regression',
                              'before': 'RED', 'after': 'C1'}}
    close('debug', 'The new test failed before the fix; the missing-key case and both existing tests pass after the two-line correction.', [finding])
    observations.append({'case': 'debug', 'red_report': str(Path(red['report']).relative_to(root)),
                         'green_report': str(Path(green['report']).relative_to(root))})

    new('experiment', 'experiment', 'Compare scan and prefix indexing by measured operations',
        'Both variants return equal sums and candidate uses fewer declared integer additions on the fixed input')
    p.atomic(root / 'input.json', {'values': list(range(1, 31)), 'queries': [10, 20, 30] * 5})
    (root / 'measure.py').write_text('''import json,sys
from pathlib import Path
data=json.loads(Path('input.json').read_text()); values=data['values']; queries=data['queries']; operations=0
if sys.argv[2]=='baseline':
    actual=[]
    for end in queries:
        value=0
        for item in values[:end]: value+=item; operations+=1
        actual.append(value)
else:
    prefix=[0]
    for item in values: prefix.append(prefix[-1]+item); operations+=1
    actual=[prefix[end] for end in queries]
assert actual==[sum(values[:end]) for end in queries]
Path(sys.argv[1]).write_text(json.dumps({'metrics':{'additions':{'value':operations,'unit':'count'},'correctness':{'value':1,'unit':'ratio'}}}))
''')
    (root / 'experiment-result.md').write_text('''# Interpretation contract
This deterministic operation-count experiment tests fixed prefix-sum queries only.
Count the additions in the actual baseline/candidate loops, including prefix construction.
Both paths assert equality with independently expressed expected sums.
No latency, memory, significance, token saving or general model-quality claim follows.
The experiment does not use randomness; one declared seed records a single repeat.
The result must show a positive additions improvement and correctness=1 in both variants.
''')
    protocol = {'version': 1, 'question': 'Do repeated prefix queries need fewer additions with a prefix index?',
                'population': '30 fixed integers and 15 prefix queries', 'limitations': 'Known-answer deterministic pilot; no latency or model claim.',
                'evaluation_type': 'fixture', 'inputs': ['input.json'], 'baseline': 'baseline', 'seeds': [11],
                'timeout': 5, 'budget_seconds': 10,
                'metrics': {'additions': {'unit': 'count', 'direction': 'minimize', 'minimum': 0},
                            'correctness': {'unit': 'ratio', 'direction': 'maximize', 'minimum': 1, 'maximum': 1}},
                'variants': {name: {'parameters': {'algorithm': name}, 'command': ['{python}', 'measure.py', '{metrics}', name]}
                             for name in ('baseline', 'candidate')}}
    p.atomic(root / 'recipe.json', protocol)
    baseline = experiments.run(root, 'recipe.json', 'baseline')
    candidate = experiments.run(root, 'recipe.json', 'candidate')
    comparison = experiments.compare(root, baseline['report'], candidate['report'])
    if comparison['metrics']['additions']['improvement'] <= 0:
        raise ValueError('pilot experiment did not meet its declared comparison criterion')
    attach('experiment', 'X1', 'experiment', baseline['report'], 'Validate the baseline raw metrics and quality limit')
    attach('experiment', 'X2', 'experiment', candidate['report'], 'Validate candidate metrics on identical declared inputs')
    attach('experiment', 'X3', 'artifact', comparison['report'], 'Compare the same protocol and all declared repeats')
    attach('experiment', 'X4', 'artifact', 'experiment-result.md', 'Restrict interpretation to measured additions and verified equal results')
    close('experiment', 'Both exact-result checks passed. The comparison counts actual additions and meets the positive improvement criterion on the fixed input only.')

    new('review', 'review', 'Review missing-key correction and scope', 'Identify the concrete defect, narrow fix, regression evidence and untested service behavior')
    (root / 'review-result.md').write_text('''# Review
The original read function indexed fetchone() without checking None, violating the missing-key contract.
The fix changes only the absent-row branch. Parameterized SQL and connection context managers remain.
Observed regression evidence: the new test fails before correction; all three tests pass after correction.
This fixture has no UI/API/auth system. Duplicate-key translation, concurrent writers and crash durability are not tested.
The implementation task accepted only its two stated conditions; it did not claim the complete design contract.
This is a scripted self-review, not independent quality assurance.
''')
    attach('review', 'R1', 'artifact', 'review-result.md', 'Inspect the original/updated branch, design requirement and real red/green reports')
    close('review', 'The review states a specific failure cause and checked regression scope, and identifies untested behavior without inventing service coverage.')
    cases = [{'id': name, 'kind': name, 'task': name} for name in tasks.KINDS]
    p.atomic(root / 'suite.json', {'version': 1, 'evaluation_type': 'fixture',
             'population': 'Six scripted local work-type cases: research, design, storage implementation/debug, experiment and review',
             'limitations': 'Known-answer replay with authored reviews; no independent agent benchmark, paid calls or product E2E.', 'cases': cases})
    result = evaluation.run(root, 'suite.json', 'six-work-type-workflow-pilot')
    output = {'status': result['status'], 'workspace': str(root.relative_to(repository.resolve())),
              'harness_source_digest': p.signature(p.snapshot(repository.resolve())),
              'evaluation_report': str((root / result['report']).relative_to(repository.resolve())),
              'cases': result['total'], 'passed': result['passed'], 'observations': observations,
              'experiment': comparison['metrics'], 'evaluation_type': 'fixture',
              'note': 'Scripted workflow integration evidence, not independent agent effectiveness.'}
    p.atomic(root / '.runtime/pilot-summary.json', output)
    return output
