// Adapt routes, labels, payload and cleanup to the app before registering this test.
// Use isolated test data and an authorized test account; never production data.
import { test, expect } from '@playwright/test';

test('@smoke creates an item and keeps it after reload', async ({ page, request }) => {
  const title = `e2e-${crypto.randomUUID()}`;
  let itemId: string | undefined;
  try {
    await page.goto('/items');
    await page.getByLabel('Title', { exact: true }).fill(title);
    const created = page.waitForResponse(response =>
      new URL(response.url()).pathname === '/api/items' && response.request().method() === 'POST');
    await page.getByRole('button', { name: 'Create', exact: true }).click();
    const response = await created;
    expect(response.status()).toBe(201);
    const body = await response.json();
    itemId = body.id;
    expect(itemId).toBeTruthy();
    await expect(page.getByRole('listitem').filter({ hasText: title })).toBeVisible();
    await page.reload();
    await expect(page.getByRole('listitem').filter({ hasText: title })).toBeVisible();
  } finally {
    // Replace with the project's fixture/API cleanup, including partial-create failures.
    if (itemId) {
      const removed = await request.delete(`/api/items/${encodeURIComponent(itemId)}`);
      expect(removed.ok()).toBeTruthy();
    }
  }
});
