"""Short verification requests get a usable default without weakening repair gates."""
from pathlib import Path
import shutil
import tempfile
import unittest

from _support import SOURCE
from harness import context, skill_flows, tasks


class VerificationDefaults(unittest.TestCase):
    def test_default_review_selects_acceptance_without_manual_topics(self):
        docs = context.select(SOURCE, 'review', [], [], read=True)['documents']
        actual = {d['path']: d for d in docs}
        entry = '.agents/skills/verify-work/references/acceptance.md'
        self.assertIn(entry, actual)
        self.assertTrue(actual[entry]['content'].strip())
        # The review entry contract does not expand unrelated research or implementation context.
        for kind in ['research', 'implement']:
            paths = {d['path'] for d in context.select(SOURCE, kind, [], [])['documents']}
            self.assertNotIn(entry, paths)

    def test_inspection_starts_with_request_and_repair_still_needs_alignment(self):
        with tempfile.TemporaryDirectory(prefix='verify-defaults-') as directory:
            root = Path(directory).resolve()
            shutil.copytree(SOURCE / '.agents', root / '.agents')
            tasks.create(root, 'existing-result', 'review', '검증해줘', ['Explain actual verification and limits'])
            result = skill_flows.start(root, 'inspect', 'existing-result', 'verify-work:inspect')
            self.assertEqual(result['node'], 'verify-work:inspect')
            with self.assertRaises(ValueError):
                skill_flows.act(root, 'inspect', 'move', edge_id='inspect-repair', reason='A confirmed defect needs repair')
            self.assertEqual(skill_flows.inspect(root, 'inspect')['node'], 'verify-work:inspect')
            with self.assertRaises(ValueError):
                skill_flows.start(root, 'implementation-check', 'existing-result', 'verify-work:check')


if __name__ == '__main__':
    unittest.main()
