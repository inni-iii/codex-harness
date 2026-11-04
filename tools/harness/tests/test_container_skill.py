"""Container skill discovery, execution gates and the actual local Compose example."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from _support import SOURCE
from harness import context, flow_catalog, skill_flows, tasks


SKILL = '.agents/skills/docker-containers/SKILL.md'
REFS = '.agents/skills/docker-containers/references/'


class ContainerSkillTests(unittest.TestCase):
    def selected(self, paths=(), topics=()):
        result = context.select(SOURCE, 'review', list(paths), list(topics), read=True)
        self.assertTrue(all(row.get('content') for row in result['documents']))
        return {row['path'] for row in result['documents']}

    def test_real_docker_file_names_select_the_skill(self):
        for path in ['Dockerfile', 'Dockerfile.gpu', 'backend/Dockerfile',
                     'infra/docker/frontend.Dockerfile', 'deploy/api.dockerfile',
                     'compose.yaml', 'compose.dev.yml', 'infra/compose.prod.yaml',
                     'docker-compose.local.yml', 'deploy/docker-compose.yaml',
                     '.dockerignore', 'backend/.dockerignore']:
            with self.subTest(path=path):
                self.assertIn(SKILL, self.selected(paths=[path]))

    def test_specialist_topics_activate_the_owner_and_only_needed_reference(self):
        for topic, expected in [('docker-images', 'images.md'),
                                ('compose', 'compose.md'),
                                ('container-verification', 'verification.md'),
                                ('container-diagnosis', 'verification.md')]:
            with self.subTest(topic=topic):
                selected = self.selected(topics=[topic])
                self.assertIn(SKILL, selected)
                self.assertIn(REFS + expected, selected)
                for other in {'images.md', 'compose.md', 'verification.md'} - {expected}:
                    self.assertNotIn(REFS + other, selected)

    def test_unrelated_project_work_does_not_load_container_procedures(self):
        for path in ['backend/items.py', 'frontend/Card.svelte', 'docs/overview.md']:
            with self.subTest(path=path):
                selected = self.selected(paths=[path])
                self.assertNotIn(SKILL, selected)
                self.assertFalse(any(name.startswith(REFS) for name in selected))

    def test_configure_needs_design_inputs_while_read_only_routes_can_start(self):
        with tempfile.TemporaryDirectory(prefix='container-flow-') as directory:
            root = Path(directory)
            shutil.copytree(SOURCE / '.agents', root / '.agents')
            (root / 'AGENTS.md').write_text('Isolated synthetic skill selection fixture.\n')
            tasks.create(root, 'demo', 'research', 'Inspect synthetic Docker configuration', ['Describe it without mutation'])
            path = root / 'docs/tasks/demo/task.json'
            task = json.loads(path.read_text())
            task['acceptance'][0]['method'] = 'Observe route preparation only'
            path.write_text(json.dumps(task))
            for route in ['inspect', 'design', 'diagnose']:
                result = skill_flows.start(root, route, 'demo', 'docker-containers:' + route)
                self.assertEqual(result['flow_status'], 'running')
            with self.assertRaisesRegex(ValueError, 'missing route inputs: alignment, design'):
                skill_flows.start(root, 'configure', 'demo', 'docker-containers:configure')

    def test_configure_must_verify_before_documenting_and_finishing(self):
        catalog = flow_catalog.load(SOURCE)
        route = catalog['nodes']['docker-containers:configure']
        self.assertIn('alignment', route['entry_checks'])
        self.assertEqual(route['required_calls'], ['verify-work:check'])
        self.assertFalse(route['finish'])
        exits = flow_catalog.outgoing(catalog, 'docker-containers:configure')
        self.assertTrue(any(e['to'] == 'verify-work:check' and e['mode'] == 'call' for e in exits))
        self.assertTrue(any(e['to'] == 'docs-maintenance:sync' and 'validated' in e['guards'] for e in exits))


@unittest.skipUnless(shutil.which('docker'), 'Docker CLI is required for static Compose model validation')
class ComposeExampleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='container-compose-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        fixture_file = self.root / 'synthetic-secret.txt'
        fixture_file.write_text('synthetic-local-example-only\n')
        self.env = os.environ.copy()
        for name in ['COMPOSE_FILE', 'COMPOSE_ENV_FILES', 'COMPOSE_PROFILES', 'COMPOSE_PROJECT_NAME']:
            self.env.pop(name, None)
        self.env.update({
                    'FRONTEND_IMAGE': 'example-web:fixture',
                    'BACKEND_IMAGE': 'example-api:fixture',
                    'POSTGRES_IMAGE': 'postgres:16-alpine',
                    'DB_PASSWORD_FILE': str(fixture_file),
                    'CREDENTIAL_FILE_PATH': '/run/secrets/db_password',
                    'WEB_PORT': '3000'})
        self.example = SOURCE / '.agents/skills/docker-containers/assets/compose.local.example.yaml'

    def config(self, project='fixture', env=None):
        return subprocess.run([shutil.which('docker'), 'compose', '-p', project,
                               '--env-file', '/dev/null', '-f', str(self.example),
                               'config', '--format', 'json'], cwd=self.root,
                              env=self.env if env is None else env,
                              text=True, capture_output=True, timeout=30)

    def model(self, project='fixture'):
        result = self.config(project)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_example_is_a_real_valid_model_with_internal_db_and_runtime_secret(self):
        model = self.model()
        services = model['services']
        self.assertEqual(set(services), {'web', 'api', 'db'})
        self.assertFalse(services['db'].get('ports'))
        self.assertTrue(model['networks']['data']['internal'])
        self.assertEqual(set(services['db']['networks']), {'data'})
        self.assertEqual(services['web']['ports'][0]['host_ip'], '127.0.0.1')
        self.assertFalse(services['api'].get('ports'))
        self.assertEqual(services['api']['depends_on']['db']['condition'], 'service_healthy')
        self.assertEqual(services['db']['environment']['POSTGRES_PASSWORD_FILE'], '/run/secrets/db_password')
        for name in ['api', 'db']:
            self.assertNotIn('POSTGRES_PASSWORD', services[name]['environment'])
            self.assertNotIn('DB_PASSWORD', services[name]['environment'])
        self.assertTrue(services['db']['volumes'])

    def test_missing_required_runtime_input_is_rejected_without_starting_services(self):
        env = {k: v for k, v in self.env.items() if k != 'DB_PASSWORD_FILE'}
        result = self.config(env=env)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('DB_PASSWORD_FILE', result.stderr)

    def test_project_names_separate_volumes_but_do_not_change_published_ports(self):
        first, second = self.model('first'), self.model('second')
        self.assertNotEqual(first['volumes']['db_data']['name'], second['volumes']['db_data']['name'])
        self.assertNotEqual(first['networks']['data']['name'], second['networks']['data']['name'])
        self.assertEqual(first['services']['web']['ports'], second['services']['web']['ports'])
        for model in [first, second]:
            self.assertFalse(any('container_name' in service for service in model['services'].values()))


if __name__ == '__main__':
    unittest.main()
