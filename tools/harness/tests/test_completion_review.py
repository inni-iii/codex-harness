"""Closure needs a final review and retained regressions for confirmed defects."""
import copy
from pathlib import Path
import unittest

from _support import SOURCE
from test_evidence import EvidenceFixture
from harness import checks, completion_review, evidence, provenance as p, tasks


class ReviewLoopTests(EvidenceFixture):
    def test_legacy_contract_hash_is_preserved_without_a_finding_registry(self):
        task = p.load(self.path)
        task.pop('findings')
        old = {key: task.get(key) for key in ('kind', 'goal', 'scope', 'constraints', 'inputs', 'depends_on')}
        old['acceptance'] = [{k:c.get(k) for k in ('id', 'condition', 'method')} for c in task['acceptance']]
        self.assertEqual(evidence.contract(task), p.signature(old))

    def prepared(self):
        self.attach()
        return self.review()

    def edit(self, review, transform):
        data = p.load(self.root / review)
        transform(data['verification'])
        # Register fixture IDs independently of the review being tested.
        task = p.load(self.path)
        task['findings'] = [f['id'] for f in data['verification']['findings']]
        p.atomic(self.path, task)
        data['task_contract'] = evidence.contract(task)
        p.atomic(self.root / review, data)

    def finish(self, review):
        return evidence.finish(self.root, 'unit', review=review, complete=True)

    def test_unfilled_audit_cannot_be_certified_by_passing_criteria_alone(self):
        review = self.prepared()
        self.edit(review, lambda audit: audit.update(completion_review.template('implement')))
        self.assertEqual(self.finish(review)['status'], 'needs_revision')

    def test_missing_area_or_unexplained_exclusion_blocks_completion(self):
        review = self.prepared()
        original = p.load(self.root / review)
        for problem in ('missing', 'pending', 'unexplained'):
            data = copy.deepcopy(original)
            areas = data['verification']['areas']
            if problem == 'missing': areas.pop()
            elif problem == 'pending': areas[0]['result'] = 'pending'
            else: areas[0].update(result='not_applicable', reason='')
            p.atomic(self.root / review, data)
            with self.subTest(problem=problem):
                self.assertEqual(self.finish(review)['status'], 'needs_revision')

    def test_final_review_round_is_required_after_new_findings(self):
        (self.root / 'follow-up.md').write_text('An unrelated issue needs a separate owner and scope.\n')
        self.attach()
        evidence.add(self.root, 'unit', 'FOLLOW', 'artifact', 'follow-up.md', 'A1', 'Review the task scope', 'Persistent follow-up')
        review = self.review()
        def change(audit):
            audit['findings'] = [{'id': 'F1', 'summary': 'Observed defect', 'cause': 'Observed cause',
                                  'status': 'out_of_scope', 'follow_up': 'FOLLOW'}]
            audit['rounds'][0].update(new_findings=['F1'], closed_findings=['F1'], outcome='new_findings')
        self.edit(review, change)
        result = self.finish(review)
        self.assertEqual(result['status'], 'needs_revision')
        self.assertIn('re-review', result['errors'][0])

    def test_fixed_finding_without_regression_is_not_complete(self):
        review = self.prepared()
        self.edit(review, lambda audit: audit['findings'].append(
            {'id': 'F1', 'summary': 'Observed defect', 'cause': 'Observed cause', 'status': 'fixed'}))
        self.assertIn('regression', self.finish(review)['errors'][0])

    def test_unknown_or_unrecorded_round_findings_are_rejected(self):
        review = self.prepared()
        self.edit(review, lambda audit: audit['rounds'][0].update(closed_findings=['unknown']))
        self.assertEqual(self.finish(review)['status'], 'needs_revision')

    def test_legacy_review_is_historical_only_and_cannot_bypass_current_policy(self):
        review = self.prepared()
        data = p.load(self.root / review)
        data['version'] = 1
        data.pop('verification')
        p.atomic(self.root / review, data)
        self.assertEqual(self.finish(review)['status'], 'needs_revision')

    def test_no_defects_does_not_require_artificial_regressions_or_multiple_runs(self):
        review = self.prepared()
        self.assertEqual(self.finish(review)['status'], 'passed')

    def test_review_cannot_drop_a_confirmed_finding_from_the_task_record(self):
        review = self.prepared()
        task = p.load(self.path)
        task['findings'] = ['F1']
        p.atomic(self.path, task)
        document = p.load(self.root / review)
        document['task_contract'] = evidence.contract(task)
        p.atomic(self.root / review, document)
        result = self.finish(review)
        self.assertEqual(result['status'], 'needs_revision')
        self.assertIn('retain', result['errors'][0])


class RegressionProofTests(EvidenceFixture):
    def test_named_junit_case_requires_its_own_failure_and_clean_pass(self):
        path = self.root / 'cases.xml'
        record = {'test_summary': 'junit', 'test_report': str(path)}
        path.write_text('<testsuite><testcase classname="ValueRegression" name="target"><failure/></testcase><testcase name="unrelated"/></testsuite>')
        self.assertTrue(completion_review.observed_case(record, 'ValueRegression.target', failed=True))
        self.assertFalse(completion_review.observed_case(record, 'unrelated', failed=True))
        path.write_text('<testsuite><testcase classname="ValueRegression" name="target"><skipped/></testcase></testsuite>')
        self.assertFalse(completion_review.observed_case(record, 'ValueRegression.target', failed=False))
        path.write_text('<testsuite><testcase classname="ValueRegression" name="target"/></testsuite>')
        self.assertTrue(completion_review.observed_case(record, 'ValueRegression.target', failed=False))

    def prepared_defect(self):
        data = p.load(self.path)
        data['kind'] = 'debug'
        data['findings'] = ['F1']
        data['goal'] = 'Correct the returned value'
        data['acceptance'][0]['condition'] = 'The function returns one'
        p.atomic(self.path, data)
        (self.root / 'app.py').write_text('VALUE = 0\n')
        (self.root / 'test_regression.py').write_text('''import unittest, app
class ValueRegression(unittest.TestCase):
    def test_expected_value(self):
        """Value contract is checked before and after correction."""
        self.assertEqual(app.VALUE, 1)
    def test_unrelated_behavior(self): self.assertTrue(True)
''')
        (self.root / 'tools/harness/harness.toml').write_text('''version=1
[[checks]]
id="persistence"
command=["{python}","-m","unittest","test_regression","-v"]
paths=["**"]
test_summary="unittest"
''')
        red = checks.run(self.root, ['app.py', 'test_regression.py'])
        self.assertEqual(red['status'], 'failed')
        evidence.add(self.root, 'unit', 'RED', 'artifact', Path(red['report']).relative_to(self.root).as_posix(),
                     'A1', 'Reproduce the incorrect value', 'Actual pre-fix failed test')
        (self.root / 'app.py').write_text('VALUE = 1  # corrected\n')
        self.attach()
        review = self.review()
        case = {'mode': 'automated', 'test_path': 'test_regression.py', 'test_id': 'ValueRegression.test_expected_value',
                'sha256': p.sha(self.root / 'test_regression.py'), 'check': 'persistence', 'before': 'RED', 'after': 'E1'}
        document = p.load(self.root / review)
        audit = document['verification']
        audit['findings'] = [{'id': 'F1', 'summary': 'The function returned zero', 'cause': 'Wrong return value',
                              'status': 'fixed', 'regression': case}]
        audit['rounds'] = [
            {'id': 'R1', 'new_findings': ['F1'], 'closed_findings': [], 'outcome': 'new_findings',
             'reason': 'Observed the expected-value assertion fail.', 'evidence': ['RED']},
            {'id': 'R2', 'new_findings': [], 'closed_findings': ['F1'], 'outcome': 'no_new_findings',
             'reason': 'The unchanged test passes after the fix; reviewed related inputs and final evidence.', 'evidence': ['E1']}]
        p.atomic(self.root / review, document)
        return review

    def test_actual_red_green_and_final_review_can_complete_then_remain_historical(self):
        review = self.prepared_defect()
        result = evidence.finish(self.root, 'unit', review=review, complete=True)
        self.assertEqual(result['status'], 'passed', result)
        (self.root / 'test_regression.py').write_text('# A later revision of tests\n')
        self.assertEqual(tasks.validate(p.load(self.path), root=self.root, task_path=self.path), [])

    def test_later_finding_preserves_old_evidence_and_rechecks_both_regressions(self):
        review = self.prepared_defect()
        task = p.load(self.path)
        task['findings'].append('F2')
        task['evidence']['E1']['type'] = 'artifact'
        p.atomic(self.path, task)
        (self.root / 'app.py').write_text('VALUE = 1\nOTHER = 0\n')
        (self.root / 'test_second.py').write_text('''import unittest, app
class SecondRegression(unittest.TestCase):
    def test_other_value(self): self.assertEqual(app.OTHER, 1)
''')
        config = self.root / 'tools/harness/harness.toml'
        config.write_text(config.read_text().replace('"test_regression","-v"', '"test_regression","test_second","-v"'))
        red = checks.run(self.root, ['app.py', 'test_second.py'])
        self.assertEqual(red['status'], 'failed')
        evidence.add(self.root, 'unit', 'RED2', 'artifact', Path(red['report']).relative_to(self.root).as_posix(),
                     'A1', 'Reproduce the second observed contract', 'Second-round failing test')
        (self.root / 'app.py').write_text('VALUE = 1\nOTHER = 1  # second correction\n')
        green = checks.run(self.root, ['app.py', 'test_second.py'])
        evidence.add(self.root, 'unit', 'GREEN2', 'check', Path(green['report']).relative_to(self.root).as_posix(),
                     'A1', 'Run both regression files', 'Both discovered defects checked together', check='persistence')
        task = p.load(self.path)
        document = p.load(self.root / review)
        document['task_contract'] = evidence.contract(task)
        document['evidence_digest'] = p.signature(task['evidence'])
        document['criteria'][0]['evidence'] = task['acceptance'][0]['evidence']
        audit = document['verification']
        audit['findings'][0]['regression']['after'] = 'GREEN2'
        audit['findings'].append({'id': 'F2', 'summary': 'The other value was zero', 'cause': 'Second incorrect value',
                                  'status': 'fixed', 'regression': {'mode': 'automated', 'test_path': 'test_second.py',
                                  'test_id': 'SecondRegression.test_other_value', 'sha256': p.sha(self.root / 'test_second.py'),
                                  'check': 'persistence', 'before': 'RED2', 'after': 'GREEN2'}})
        audit['rounds'].extend([
            {'id': 'R3', 'new_findings': ['F2'], 'closed_findings': [], 'outcome': 'new_findings',
             'reason': 'A later review found a second contract violation.', 'evidence': ['RED2']},
            {'id': 'R4', 'new_findings': [], 'closed_findings': ['F2'], 'outcome': 'no_new_findings',
             'reason': 'Both regression cases pass together in the final run.', 'evidence': ['GREEN2']}])
        p.atomic(self.root / review, document)
        result = evidence.finish(self.root, 'unit', review=review, complete=True)
        self.assertEqual(result['status'], 'passed', result)

    def test_changed_test_or_missing_before_evidence_cannot_claim_regression(self):
        review = self.prepared_defect()
        original = p.load(self.root / review)
        for problem in ('test-changed', 'no-before', 'same-before-after', 'not-closed', 'wrong-case'):
            document = copy.deepcopy(original)
            finding = document['verification']['findings'][0]
            if problem == 'test-changed': finding['regression']['sha256'] = '0' * 64
            elif problem == 'no-before': finding['regression']['before'] = 'missing'
            elif problem == 'same-before-after': finding['regression']['before'] = 'E1'
            elif problem == 'wrong-case': finding['regression']['test_id'] = 'ValueRegression.test_unrelated_behavior'
            else: document['verification']['rounds'][-1]['closed_findings'] = []
            p.atomic(self.root / review, document)
            with self.subTest(problem=problem):
                self.assertEqual(evidence.finish(self.root, 'unit', review=review)['status'], 'needs_revision')

    def test_execution_failure_is_not_an_observed_behavior_regression(self):
        review = self.prepared_defect()
        task = p.load(self.path)
        entry = task['evidence']['RED']
        red_path = self.root / entry['path']
        report = p.load(red_path)
        report['results'][0]['execution_error'] = 'timeout'
        p.atomic(red_path, report)
        entry['sha256'] = p.sha(red_path)
        p.atomic(self.path, task)
        document = p.load(self.root / review)
        document['evidence_digest'] = p.signature(task['evidence'])
        p.atomic(self.root / review, document)
        result = evidence.finish(self.root, 'unit', review=review)
        self.assertEqual(result['status'], 'needs_revision')
        self.assertIn('execution/report', result['errors'][0])

    def test_manual_regression_needs_a_real_case_and_explicit_automation_limit(self):
        (self.root / 'scenario.md').write_text('# Scenario\nRead the returned value. Expected: one. Record before/after observations.\n')
        review = self.prepared_defect()
        evidence.add(self.root, 'unit', 'CASE', 'artifact', 'scenario.md', 'A1', 'Review the recorded scenario', 'Manual-mode contract fixture')
        task = p.load(self.path)
        document = p.load(self.root / review)
        document['task_contract'] = evidence.contract(task)
        document['evidence_digest'] = p.signature(task['evidence'])
        document['criteria'][0]['evidence'] = task['acceptance'][0]['evidence']
        case = {'mode': 'manual', 'case': 'CASE', 'before': 'RED', 'after': 'CASE',
                'expected': 'Return one in the documented scenario', 'why_not_automated': ''}
        document['verification']['findings'][0]['regression'] = case
        p.atomic(self.root / review, document)
        self.assertEqual(evidence.finish(self.root, 'unit', review=review)['status'], 'needs_revision')
        case['why_not_automated'] = 'Schema fixture for explicit manual exception handling; not a real environment limitation claim.'
        p.atomic(self.root / review, document)
        result = evidence.finish(self.root, 'unit', review=review)
        self.assertEqual(result['status'], 'passed', result)
