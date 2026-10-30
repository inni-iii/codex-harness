// Launched from the repository root by a local MCP client.
import { createRequire } from 'node:module';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawn } from 'node:child_process';

const root = fileURLToPath(new URL('../../..', import.meta.url));
try {
  const require = createRequire(new URL('../browser/package.json', import.meta.url));
  const pkg = require.resolve('@playwright/mcp/package.json');
  const child = spawn(process.execPath, [resolve(dirname(pkg), 'cli.js'), '--isolated', '--headless', '--browser', 'chromium', '--output-dir', resolve(root, '.runtime/browser')], {
    cwd: root, stdio: 'inherit',
    env: { ...process.env, PLAYWRIGHT_BROWSERS_PATH: resolve(root, '.cache/playwright') },
  });
  for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => child.kill(signal));
  child.on('error', (err) => { process.stderr.write(`${err.message}\n`); process.exitCode = 1; });
  child.on('exit', (code) => { process.exitCode = code ?? 1; });
} catch (err) {
  process.stderr.write(`Browser tools unavailable: run python3 tools/harness/run.py setup --browser\n${err.message}\n`);
  process.exitCode = 1;
}
