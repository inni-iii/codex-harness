"""Recorded survey data must not block checks or hide unregistered code/data."""
import unittest

from _support import SOURCE
from harness import checks


class ConnectionRepairs(unittest.TestCase):
    def test_survey_artifacts_allow_full_checks_without_exempting_other_json(self):
        artifacts = ['docs/tasks/docker-infra-survey/inventory.json',
                     'docs/tasks/docker-infra-survey/observations.json']
        plan = checks.plan(SOURCE, artifacts, full=True)
        self.assertEqual(plan['uncovered_paths'], [])
        self.assertIn('python', {c['id'] for c in plan['checks']})
        unknown = 'docs/tasks/docker-infra-survey/unregistered.json'
        self.assertEqual(checks.plan(SOURCE, [unknown], full=True)['uncovered_paths'], [unknown])
        helper = 'docs/tasks/docker-infra-survey/helper.py'
        self.assertEqual(checks.plan(SOURCE, [helper], full=True)['uncovered_paths'], [helper])


if __name__ == '__main__':
    unittest.main()
