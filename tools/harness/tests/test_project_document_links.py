"""Document writing links real files/maps/reading rules and preserves invalid updates."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import shutil
import tempfile
import tomllib
import unittest
from unittest.mock import patch

from _support import SOURCE
from harness import cli, context, document_indexes, project_documents as docs, workflows


class ProjectDocumentLinks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='document-links-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        for name in ['plan-project', 'security-review']:
            shutil.copytree(SOURCE / '.agents/skills' / name / 'assets', self.root / '.agents/skills' / name / 'assets')
            (self.root / '.agents/skills' / name / 'SKILL.md').write_text('# Fixture\n')
        (self.root / '.agents/context.toml').write_text('version=1\n' + ''.join(
            f'[[skills]]\nname="{n}"\nwhen="Fixture"\ntopics=["{n}"]\n' for n in ['plan-project', 'security-review']))
        self.write('AGENTS.md', '# Fixture\n')
        self.write('tools/harness/harness.toml', 'version=1\nchecks=[]\n')
        self.profile = workflows.create(self.root, 'demo', 'Observe a user result').relative_to(self.root).as_posix()
        self.source = self.write('.runtime/body.md', '# Login\nInputs and expected outcomes.\n')

    def write(self, relative, text):
        p = self.root / relative
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        return p

    def upsert(self, **kwargs):
        args = dict(root=self.root, profile=self.profile, feature='login', kind='spec',
                    source='.runtime/body.md', role='Login input and expected result', paths=['backend/auth/**'])
        args.update(kwargs)
        return docs.upsert(**args)

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes()
                for p in (self.root / 'docs').rglob('*') if p.is_file()}

    def test_write_rewrite_and_context_select_only_relevant_feature(self):
        result = self.upsert()
        self.assertEqual(result['document'], 'docs/demo/features/login/spec.md')
        self.assertFalse(result['updated'])
        self.assertEqual(document_indexes.inspect(self.root)['errors'], [])
        self.upsert(feature='export', role='Export formats and failures', paths=['backend/export/**'])
        self.source.write_text('# Login revised\nKeep one current contract.\n')
        self.assertTrue(self.upsert()['updated'])
        first = self.snapshot()
        self.upsert()
        self.assertEqual(self.snapshot(), first)
        self.assertEqual((self.root / self.profile).read_text().count('# harness-document: docs/demo/features/login/spec.md'), 1)
        self.assertEqual((self.root / 'docs/demo/features/login/index.md').read_text().count('(spec.md)'), 1)
        selected = context.select(self.root, 'research', ['backend/auth/session.py'], [], workflow=self.profile, read=True)
        paths = [d['path'] for d in selected['documents']]
        self.assertIn(result['document'], paths)
        self.assertNotIn('docs/demo/features/export/spec.md', paths)
        self.assertNotIn('docs/demo/features/export/index.md', paths)
        self.assertLess(paths.index('docs/demo/features/login/index.md'), paths.index(result['document']))
        self.assertEqual(docs.inspect(self.root, self.profile, workflows.load(self.root, self.profile))['errors'], [])

    def test_update_conditions_and_role_replace_owned_binding_without_duplicates(self):
        self.upsert()
        self.upsert(paths=['api/session/**'], topics=['login'], role='Current session and login rules')
        profile = workflows.load(self.root, self.profile)
        rules = profile['context']['rules']
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0]['paths'], ['api/session/**'])
        self.assertEqual(rules[0]['topics'], ['login'])
        self.assertEqual(rules[0]['when'], 'Current session and login rules')
        self.assertIn('Current session and login rules', (self.root / 'docs/demo/features/login/index.md').read_text())
        self.upsert(paths=[], topics=[])
        self.assertEqual(workflows.load(self.root, self.profile)['context']['rules'][0]['paths'], ['api/session/**'])

    def test_missing_conditions_bad_roles_and_bad_names_leave_documents_unchanged(self):
        before = self.snapshot()
        for changes in [dict(paths=[], topics=[]), dict(role='TODO'), dict(role='bad\nrole'),
                        dict(feature='../escape'), dict(kind='final-v2'), dict(paths=['../outside'])]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.upsert(**changes)
            self.assertEqual(self.snapshot(), before)

    def test_source_limit_empty_content_and_invalid_utf8_are_rejected(self):
        for raw in [b'', b'\xff', b'x' * (docs.LIMIT + 1)]:
            before = self.snapshot()
            self.source.write_bytes(raw)
            with self.assertRaises((ValueError, UnicodeError)):
                self.upsert()
            self.assertEqual(self.snapshot(), before)

    def test_symlink_source_and_target_cannot_alias_other_files(self):
        source = self.root / '.runtime/alias.md'
        source.symlink_to(self.source)
        with self.assertRaises(ValueError):
            self.upsert(source='.runtime/alias.md')
        target = self.root / 'docs/demo/features'
        target.mkdir()
        with tempfile.TemporaryDirectory() as other:
            (target / 'login').symlink_to(other, target_is_directory=True)
            with self.assertRaises(ValueError):
                self.upsert()
            self.assertEqual(list(Path(other).iterdir()), [])

    def test_busy_writer_does_not_change_source_or_remove_other_lock(self):
        lock = self.write('.runtime/document-write.lock', 'active')
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'another document writer'):
            self.upsert()
        self.assertTrue(lock.exists())
        self.assertEqual(self.snapshot(), before)

    def test_partial_write_failure_rolls_back_only_its_changes(self):
        before = self.snapshot()
        replace = docs._replace
        calls = 0
        def interrupted(path, text):
            nonlocal calls
            calls += 1
            if calls == 3:
                raise PermissionError('synthetic write denial')
            replace(path, text)
        with patch.object(docs, '_replace', interrupted), self.assertRaises(PermissionError):
            self.upsert()
        self.assertEqual(self.snapshot(), before)
        self.assertFalse((self.root / '.runtime/document-write.lock').exists())
        self.assertFalse((self.root / 'docs/demo/features').exists())

    def test_manual_reading_rule_is_reused_and_conflicting_rewrite_is_rejected(self):
        self.upsert()
        file = self.root / self.profile
        text = file.read_text().replace('# harness-document: docs/demo/features/login/spec.md\n', '').replace('# /harness-document\n', '')
        file.write_text(text)
        self.upsert()
        self.assertEqual(file.read_text(), text)
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'manual document conditions'):
            self.upsert(paths=['backend/other/**'])
        self.assertEqual(self.snapshot(), before)

    def test_loose_unregistered_and_broad_feature_documents_are_reported(self):
        self.upsert()
        self.write('docs/demo/features/login/unbound.md', '# Unregistered\n')
        self.write('docs/demo/features/login/UPPERCASE.MD', '# Unregistered uppercase\n')
        self.write('docs/demo/loose.md', '# Wrong place\n')
        self.write('docs/loose.md', '# No project\n')
        errors = docs.inspect(self.root, self.profile, workflows.load(self.root, self.profile))['errors']
        for rel in ['docs/demo/features/login/unbound.md', 'docs/demo/features/login/UPPERCASE.MD', 'docs/demo/loose.md', 'docs/loose.md']:
            self.assertTrue(any(rel in e for e in errors), errors)
        file = self.root / self.profile
        file.write_text(file.read_text().replace('paths = ["backend/auth/**"]', 'kinds = ["implement"]\npaths = ["backend/auth/**"]'))
        self.assertTrue(any('login/spec.md' in e for e in docs.inspect(self.root, self.profile, workflows.load(self.root, self.profile))['errors']))

    def test_reserved_names_duplicate_and_legacy_paths_do_not_create_new_sources(self):
        for name in ['tasks', 'knowledge', 'projects']:
            with self.subTest(name=name), self.assertRaises(ValueError):
                workflows.create(self.root, name, 'Reserved')
        with self.assertRaises(FileExistsError):
            workflows.create(self.root, 'demo', 'Duplicate')
        legacy = self.write('docs/projects/old/workflow.toml', 'version=1\nname="old"\nstate="draft"\nchecks=[]\n[context]\ndocuments=[]\n')
        self.assertEqual(workflows.load(self.root, legacy.relative_to(self.root).as_posix())['name'], 'old')
        with self.assertRaises(FileExistsError):
            workflows.create(self.root, 'old', 'Avoid dual sources')
        with self.assertRaises(ValueError):
            self.upsert(profile='docs/projects/old/workflow.toml')

    def test_migration_plan_is_read_only_and_marks_loose_documents(self):
        self.write('docs/projects/old/workflow.toml', 'version=1\nname="old"\nstate="draft"\nchecks=[]\n[context]\ndocuments=[]\n')
        self.write('docs/projects/old/contract.md', '# Needs a feature owner\n')
        before = self.snapshot()
        result = docs.migration_plan(self.root, 'docs/projects/old/workflow.toml')
        self.assertEqual(result['status'], 'planned')
        row = next(r for r in result['mapping'] if r['from'].endswith('contract.md'))
        self.assertTrue(row['needs_classification'])
        self.assertEqual(row['to'], 'docs/old/contract.md')
        self.assertEqual(self.snapshot(), before)

    def test_broad_manual_binding_is_not_reported_as_success(self):
        self.upsert()
        file = self.root / self.profile
        file.write_text(file.read_text().replace('paths = ["backend/auth/**"]',
                                                'kinds = ["implement"]\npaths = ["backend/auth/**"]'))
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'selective paths/topics'):
            self.upsert()
        self.assertEqual(self.snapshot(), before)

    def test_docs_root_escape_and_unknown_layout_are_rejected(self):
        with tempfile.TemporaryDirectory() as other, tempfile.TemporaryDirectory() as fresh:
            root = Path(fresh)
            (root / 'docs').symlink_to(other, target_is_directory=True)
            with self.assertRaises(ValueError):
                workflows.create(root, 'escape', 'Stay local')
            self.assertEqual(list(Path(other).iterdir()), [])
        file = self.root / self.profile
        original = file.read_text()
        for replacement in ['layout="unknown"', 'layout="feature-folders"\nextra=true']:
            file.write_text(original.replace('layout = "feature-folders"', replacement))
            with self.assertRaises(ValueError):
                workflows.load(self.root, self.profile)
        file.write_text(original)

    def test_real_cli_writes_and_connects_document(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = cli.main(['document', 'upsert', '--project', self.profile, '--feature', 'login',
                             '--source', '.runtime/body.md', '--role', 'Login contract and error cases',
                             '--path', 'backend/auth/**'], root=self.root)
        self.assertEqual(code, 0, output.getvalue())
        result = json.loads(output.getvalue())
        self.assertTrue((self.root / result['document']).is_file())
        self.assertEqual(document_indexes.inspect(self.root)['errors'], [])


if __name__ == '__main__':
    unittest.main()
