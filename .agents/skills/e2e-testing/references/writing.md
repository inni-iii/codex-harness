# Playwright 대기와 응답 assertion

실제 E2E 테스트를 작성·수정할 때 읽는다. [시나리오](scenarios.md)의 사용자 흐름·실제 경계·데이터 조건부터 정한다.

대기를 동작 전에 등록하는 예다. 실제 역할·문구·endpoint와 합의된 status/payload로 바꾼다.

```typescript
const responsePromise = page.waitForResponse(
  r => r.url().endsWith('/api/items') && r.request().method() === 'POST'
);
await page.getByRole('button', { name: '저장', exact: true }).click();
const response = await responsePromise;
// 실제 프로젝트가 합의한 status/payload도 검사한다.
expect(response.ok()).toBeTruthy();
await expect(page.getByRole('status')).toContainText('저장');
```

[Playwright 대기 API](https://playwright.dev/docs/api/class-page#page-wait-for-load-state)의 안내처럼 networkidle 하나 대신 관측 가능한 준비 상태를 확인한다.
