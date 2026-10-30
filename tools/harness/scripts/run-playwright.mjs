#!/usr/bin/env node
// Run only the project's installed test runner; never install through npx.
import { existsSync, mkdirSync, realpathSync } from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { spawn } from 'node:child_process';

function main() {
  const args = process.argv.slice(2);
  let projectDir, report;
  const forwarded = [];
  while (args.length) {
    const arg = args.shift();
    if (arg === '--') { forwarded.push(...args); break; }
    if (arg === '--project-dir' && args[0]) projectDir = args.shift();
    else if (arg === '--report' && args[0]) report = args.shift();
    else throw new Error(`Unknown or incomplete argument: ${arg}`);
  }
  if (!projectDir || !report) throw new Error('Required: --project-dir <app> --report <fresh.xml> [-- <test filters>]');
  if (forwarded.some(arg => /^(--reporter|--output)(=|$)/.test(arg))) {
    throw new Error('Keep the configured JUnit reporter and artifact directory; do not override --reporter/--output.');
  }
  const root = realpathSync(process.cwd());
  const app = realpathSync(path.resolve(root, projectDir));
  const contained = target => target === root || target.startsWith(root + path.sep);
  if (!contained(app)) throw new Error('Project directory must be inside this repository.');
  const configs = ['ts', 'mts', 'cts', 'js', 'mjs', 'cjs'].map(ext => `playwright.config.${ext}`);
  if (!configs.some(name => existsSync(path.join(app, name)))) throw new Error('Project Playwright config is missing.');
  const require = createRequire(path.join(app, 'package.json'));
  let pkg;
  try { pkg = realpathSync(require.resolve('@playwright/test/package.json')); }
  catch { throw new Error('Project-local @playwright/test is missing. Install its pinned dependency using the project lockfile.'); }
  if (!contained(pkg)) throw new Error('The test runner resolves outside the repository; install it locally.');
  const cli = path.join(path.dirname(pkg), 'cli.js');
  if (!existsSync(cli)) throw new Error('Installed @playwright/test has no cli.js.');
  const reportPath = path.resolve(root, report);
  if (existsSync(reportPath)) throw new Error('JUnit report already exists; provide a fresh path.');
  mkdirSync(path.dirname(reportPath), { recursive: true });
  const artifacts = reportPath.replace(/\.[^/.]+$/, '') + '-artifacts';
  const child = spawn(process.execPath, [cli, 'test', ...forwarded], {
    cwd: app, stdio: 'inherit', shell: false,
    env: { ...process.env, HARNESS_JUNIT_REPORT: reportPath, HARNESS_E2E_ARTIFACTS: artifacts },
  });
  for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => child.kill(signal));
  child.on('error', error => { console.error(error.message); process.exitCode = 2; });
  child.on('exit', (code, signal) => {
    process.exitCode = code ?? (signal === 'SIGINT' ? 130 : 143);
    if (code === 0 && !existsSync(reportPath)) {
      console.error('Runner produced no fresh JUnit report. Connect HARNESS_JUNIT_REPORT in the project config.');
      process.exitCode = 2;
    }
  });
}
try { main(); } catch (error) { console.error(error.message); process.exitCode = 2; }
