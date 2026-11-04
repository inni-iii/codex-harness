"""Record fewer manual facts without manufacturing a successful review."""
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
from unittest.mock import patch

from test_evidence import EvidenceFixture
from harness import cli, evidence, evidence_records as records, provenance as p, task_timing as timing


class RecordPreparationTests(EvidenceFixture):
    def prepare(self):
        data = p.load(self.path)
        data['acceptance'][0]['method'] = 'Read actual outputs and inspect the persistence check'
        data['acceptance'].append({'id': 'A2', 'condition': 'Preserve source conditions',
                                  'method': 'Read the original source memo', 'status': 'pending', 'evidence': []})
        p.atomic(self.path, data)
        (self.root / 'result.md').write_text('Observed synthetic local result; no independent quality claim.')
        (self.root / 'source.md').write_text('Local memo for an authored source-record fixture, not a fetched source.')
        return [{'id': 'RESULT', 'type': 'artifact', 'path': 'result.md', 'criteria': ['A1', 'A2'],
                 'description': 'Observed synthetic result'},
                {'id': 'SOURCE', 'type': 'source', 'path': 'source.md', 'criteria': ['A2'],
                 'description': 'Authored source schema fixture', 'origin': 'https://example.org/original',
                 'accessed_at': '2026-11-04'}]

    def manifest(self, entries):
        path = self.root / '.runtime/import.json'
        p.atomic(path, {'version': 1, 'entries': entries})
        return path.relative_to(self.root).as_posix()

    def test_cli_import_links_many_criteria_without_changing_method_or_passing(self):
        rows = self.prepare(); before = p.load(self.path)
        out = StringIO()
        with redirect_stdout(out):
            code = cli.main(['evidence', 'import', 'unit', '--manifest', self.manifest(rows)], root=self.root)
        self.assertEqual(code, 0, out.getvalue())
        data = p.load(self.path)
        self.assertEqual(data['acceptance'][0]['evidence'], ['RESULT'])
        self.assertEqual(data['acceptance'][1]['evidence'], ['RESULT', 'SOURCE'])
        self.assertEqual([c['method'] for c in data['acceptance']], [c['method'] for c in before['acceptance']])
        self.assertEqual(data['evidence']['RESULT']['sha256'], p.sha(self.root / 'result.md'))
        self.assertTrue(all(c['status'] == 'pending' for c in data['acceptance']))
        self.assertEqual(evidence.finish(self.root, 'unit', complete=True)['status'], 'needs_revision')

    def test_invalid_later_entry_never_partially_registers_or_destroys_review(self):
        rows = self.prepare()
        old = self.root / 'docs/tasks/unit/review.json';old.write_text('Existing reviewer work')
        before = self.path.read_bytes()
        bad = [dict(rows[1], path='missing.md'), dict(rows[1], id='RESULT'),
               dict(rows[1], path='../escape.md'), dict(rows[1], criteria=['unknown']),
               dict(rows[1], criteria=['A2', 'A2']), dict(rows[1], accessed_at='invalid'),
               dict(rows[1], status='passed'), dict(rows[1], origin='not-a-url')]
        for row in bad:
            with self.subTest(row=row), self.assertRaises((ValueError, OSError)):
                records.import_entries(self.root, 'unit', self.manifest([rows[0], row]))
            self.assertEqual(self.path.read_bytes(), before)
            self.assertEqual(old.read_text(), 'Existing reviewer work')

    def test_method_and_symlink_and_concurrent_task_edit_are_not_bypassed(self):
        rows = self.prepare();data = p.load(self.path);data['acceptance'][0]['method'] = '';p.atomic(self.path, data)
        with self.assertRaisesRegex(ValueError, 'method'):
            records.import_entries(self.root, 'unit', self.manifest(rows))
        data['acceptance'][0]['method'] = 'Inspect output';p.atomic(self.path, data)
        (self.root / 'alias.md').symlink_to(self.root / 'result.md')
        with self.assertRaises(ValueError):
            records.import_entries(self.root, 'unit', self.manifest([dict(rows[0], path='alias.md')]))
        original = evidence.save_unchanged
        def newer(path, new, digest):
            current = p.load(path);current['goal'] = 'New user goal';p.atomic(path, current)
            return original(path, new, digest)
        with patch('harness.evidence.save_unchanged', side_effect=newer), self.assertRaisesRegex(ValueError, 'task changed'):
            records.import_entries(self.root, 'unit', self.manifest(rows))
        self.assertEqual(p.load(self.path)['evidence'], {})
        self.assertEqual(p.load(self.path)['goal'], 'New user goal')

    def test_new_review_draft_preserves_existing_review_and_reports_execution_facts(self):
        saved = self.attach()
        first = evidence.review_template(self.root, 'unit')['review']
        original = (self.root / first).read_bytes()
        with self.assertRaisesRegex(ValueError, 'already exists'):
            evidence.review_template(self.root, 'unit')
        out = StringIO()
        with redirect_stdout(out):
            code = cli.main(['evidence', 'review-template', 'unit', '--output', '.runtime/new-review.json'], root=self.root)
        self.assertEqual(code, 0, out.getvalue())
        draft = p.load(self.root / '.runtime/new-review.json')
        self.assertEqual((self.root / first).read_bytes(), original)
        self.assertEqual(draft['criteria'][0]['decision'], 'pending')
        self.assertEqual(draft['reviewer'], '')
        self.assertFalse(draft['independent'])
        self.assertEqual(draft['observations'][0]['duration_seconds'], saved['results'][0]['duration_seconds'])
        self.assertEqual(draft['observations'][0]['current_sources'], 'not_checked')
        self.assertEqual(evidence.finish(self.root, 'unit', review='.runtime/new-review.json')['status'], 'needs_revision')

    def test_inspect_rejects_tampered_log_and_cannot_hide_stale_sources(self):
        saved = self.attach();self.review()
        (self.root / 'verify.py').write_text('Changed code')
        self.assertEqual(records.inspect(self.root, 'unit')['observations'][0]['current_sources'], 'not_checked')
        self.assertEqual(evidence.finish(self.root, 'unit')['status'], 'needs_revision')
        Path(saved['results'][0]['log']).write_text('tampered')
        with self.assertRaises(ValueError):records.inspect(self.root, 'unit')
        with self.assertRaises(ValueError):evidence.review_template(self.root, 'unit', output='.runtime/tampered-review.json')
        self.assertFalse((self.root / '.runtime/tampered-review.json').exists())

    def test_observation_and_timing_cli_success_exit_codes(self):
        self.attach()
        codes = []
        for command in [['evidence', 'inspect', 'unit'], ['timing', 'mark', 'unit', 'verify'],
                        ['timing', 'mark', 'unit', 'verify'], ['timing', 'report', 'unit']]:
            with redirect_stdout(StringIO()):
                codes.append(cli.main(command, root=self.root))
        self.assertEqual(codes, [0, 0, 0, 0])

    def test_review_output_cannot_escape_or_use_symlinks_or_replace_existing_file(self):
        self.attach()
        (self.root / 'existing.json').write_text('Keep this')
        (self.root / 'alias').symlink_to(self.root / '.runtime', target_is_directory=True)
        for relative in ['../outside.json', 'existing.json', 'alias/review.json']:
            with self.subTest(relative=relative), self.assertRaises(ValueError):
                evidence.review_template(self.root, 'unit', output=relative)
        self.assertEqual((self.root / 'existing.json').read_text(), 'Keep this')


class TaskTimingTests(EvidenceFixture):
    def setUp(self):
        super().setUp()
        data = p.load(self.path);data['created_at'] = '2026-01-01T00:00:00+00:00';p.atomic(self.path, data)

    def at(self, seconds):
        return patch('harness.provenance.now', return_value=f'2026-01-01T00:00:{seconds:02d}+00:00')

    def test_unmarked_time_is_explicit_and_report_does_not_create_ledger(self):
        with self.at(10):result = timing.report(self.root, 'unit')
        self.assertEqual(result['wall_seconds'], 10)
        self.assertEqual(result['phase_seconds'], {'unclassified': 10})
        self.assertFalse((self.root / '.runtime/task-timing/unit.json').exists())

    def test_repeated_phases_accumulate_and_close_uses_completion_time(self):
        for second, phase in [(5, 'research'), (10, 'implement'), (15, 'research')]:
            with self.at(second):timing.mark(self.root, 'unit', phase)
        with self.at(17):self.assertEqual(timing.mark(self.root, 'unit', 'research')['status'], 'unchanged')
        data = p.load(self.path);data.update(status='complete', completed_at='2026-01-01T00:00:20+00:00');p.atomic(self.path, data)
        with self.at(30):result = timing.report(self.root, 'unit')
        self.assertEqual(result['wall_seconds'], 20)
        self.assertEqual(result['phase_seconds'], {'unclassified': 5, 'research': 10, 'implement': 5})
        with self.at(30), self.assertRaisesRegex(ValueError, 'completed'):timing.mark(self.root, 'unit', 'review')

    def test_clock_reversal_and_bad_phase_and_symlink_do_not_mutate_ledger(self):
        with self.at(10):timing.mark(self.root, 'unit', 'implement')
        path = self.root / '.runtime/task-timing/unit.json';before = path.read_bytes()
        with self.at(5), self.assertRaises(ValueError):timing.mark(self.root, 'unit', 'review')
        with self.at(20), self.assertRaises(ValueError):timing.mark(self.root, 'unit', '../escape')
        self.assertEqual(path.read_bytes(), before)
        path.unlink();path.symlink_to(self.root / 'verify.py')
        with self.at(20), self.assertRaises(ValueError):timing.mark(self.root, 'unit', 'review')
        self.assertFalse((self.root / 'verify.py').read_text().startswith('{'))

    def test_concurrent_ledger_edit_after_read_is_preserved(self):
        with self.at(5):timing.mark(self.root, 'unit', 'research')
        original = timing.state
        def external_edit(*args):
            result = original(*args)
            path = self.root / '.runtime/task-timing/unit.json'
            newer = p.load(path);newer['marks'].append({'phase': 'other-writer', 'at': '2026-01-01T00:00:07+00:00'})
            p.atomic(path, newer)
            return result
        with self.at(10), patch('harness.task_timing.state', side_effect=external_edit):
            with self.assertRaisesRegex(ValueError, 'ledger changed'):
                timing.mark(self.root, 'unit', 'verify')
        self.assertEqual(p.load(self.root / '.runtime/task-timing/unit.json')['marks'][-1]['phase'], 'other-writer')

    def test_checks_are_separate_and_duplicate_evidence_does_not_double_count(self):
        saved = self.attach();data = p.load(self.path)
        data['evidence']['SAME_RUN'] = dict(data['evidence']['E1'])
        data['acceptance'][0]['evidence'].append('SAME_RUN');p.atomic(self.path, data)
        with self.at(20):result = timing.report(self.root, 'unit')
        self.assertEqual(len(result['check_runs']), 1)
        self.assertEqual(result['recorded_check_seconds'], saved['results'][0]['duration_seconds'])
        self.assertEqual(result['wall_seconds'], 20)
        self.assertIn('overlap', result['note'])
