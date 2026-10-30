// Copy into the app package, then replace environment values with project contracts.
const { defineConfig, devices } = require('@playwright/test');
const path = require('node:path');

function localURL(value, name) {
  if (!value) throw new Error(`${name} is required.`);
  const parsed = new URL(value);
  if (!['http:', 'https:'].includes(parsed.protocol) ||
      !['localhost', '127.0.0.1', '[::1]'].includes(parsed.hostname) ||
      parsed.username || parsed.password) {
    throw new Error(`${name} must be a local test-server URL without credentials.`);
  }
  return parsed.href;
}
const baseURL = localURL(process.env.E2E_BASE_URL, 'E2E_BASE_URL');
const existing = process.env.E2E_USE_EXISTING_SERVER === 'true';
if (process.env.E2E_USE_EXISTING_SERVER && !existing) {
  throw new Error('E2E_USE_EXISTING_SERVER accepts only true; omit it for managed servers.');
}
const webServer = [];
if (!process.env.E2E_START_COMMAND && !existing) throw new Error('E2E_START_COMMAND is required for managed servers.');
if (process.env.E2E_START_COMMAND) webServer.push({
  command: process.env.E2E_START_COMMAND, url: baseURL,
  reuseExistingServer: existing, timeout: 60_000,
});
if (process.env.E2E_API_START_COMMAND && !process.env.E2E_API_URL) throw new Error('E2E_API_URL is required for the API server.');
if (process.env.E2E_API_URL) {
  const apiURL = localURL(process.env.E2E_API_URL, 'E2E_API_URL');
  if (!process.env.E2E_API_START_COMMAND && !existing) throw new Error('E2E_API_START_COMMAND is required for the API server.');
  if (process.env.E2E_API_START_COMMAND) webServer.push({
    command: process.env.E2E_API_START_COMMAND, url: apiURL,
    reuseExistingServer: existing, timeout: 60_000,
  });
}
const artifacts = process.env.HARNESS_E2E_ARTIFACTS || path.resolve('.runtime/e2e');
module.exports = defineConfig({
  testDir: './tests/e2e',
  forbidOnly: true,
  globalTimeout: 120_000, // Keep below the harness check timeout; adjust for the actual suite.
  retries: 0,
  workers: 1, // Increase after proving data/account isolation.
  fullyParallel: false,
  outputDir: path.join(artifacts, 'results'),
  reporter: [
    ['list'],
    ['junit', { outputFile: process.env.HARNESS_JUNIT_REPORT || path.join(artifacts, 'junit.xml') }],
    ['html', { outputFolder: path.join(artifacts, 'html'), open: 'never' }],
  ],
  use: { baseURL, trace: 'retain-on-failure', screenshot: 'only-on-failure' },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer,
});
