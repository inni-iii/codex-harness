# 실제 브라우저로 흐름 확인

보이는 UI·상호작용·비동기 경합을 바꿀 때 읽는다.
반복 가능한 사용자 흐름 검사는 [E2E 스킬](../../e2e-testing/SKILL.md)의 시나리오·설정·실패 분석으로 연결한다.
폼·탐색·인증·API 연결·공통 UI 동작 변경은 의미 있는 사용자 기능 묶음이 완성되는 시점에 관련 E2E를 수행한다. 작은 편집마다 반복하지 않는다.
브라우저 MCP는 화면 탐색·조작 도구이고 @playwright/test는 자동 검사 runner다. MCP 설치만으로 테스트가 실행되지 않는다.

## 시작 조건

사용할 앱 URL·서버 시작 방법·테스트 데이터·인증과 정리 범위를 확인한다.
원격 SSH 서버에서 dev server·설치·테스트를 실행하지 않는다. 로컬 검증을 준비한다.
브라우저 도구가 설치되지 않았거나 앱을 띄울 수 없으면 그 범위를 미실행으로 남긴다.
브라우저 도구가 연결됐다는 것과 실제 사용자 흐름 확인은 구분한다.

## 요구를 행동으로 확인

핵심 동작 전 상태 → 실제 입력/클릭 → 예상한 화면·네트워크·데이터 결과를 확인한다.
권한·저장·서버 연결을 검증할 때는 해당 경계를 통과하는 작은 흐름이 필요하다.
mock 기반 UI 검사와 실제 API 통합 검사를 결과에서 구분한다.
대표 성공 흐름 외에도 관련 오류·빈 상태·재시도·새로고침·중복 입력을 선택한다.

## 안정적인 Playwright 검사

role/label 같은 사용자 의미 locator를 우선하고, 모호하면 적절한 test id를 사용한다.
임의 sleep 대신 관측할 UI·응답을 기다린다.
이벤트 대기를 먼저 등록하고 동작을 시작해야 빠른 응답을 놓치지 않는다.

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

위 역할·문구·endpoint는 예시다. 실제 계약에 맞춘다.
networkidle을 모든 화면의 준비 조건으로 삼지 않는다. 폴링·스트림 화면에서는 안정된 사용자 상태를 기다린다.
[Playwright API 안내](https://playwright.dev/docs/api/class-page#page-wait-for-load-state)는 networkidle 대신 명시적 assertion 사용을 권한다.

## 시각·접근성

변경 화면의 관련 상태, 좁은/넓은 뷰포트, 긴 텍스트, 실제 지원 테마를 확인한다.
공통 token/primitive/layout이면 대표 사용처와 인접 화면도 확인한다.
키보드로 도달·동작·닫힘·focus 복원을 확인한다. screenshot만으로 동작을 증명하지 않는다.
비교 기준, viewport, 상태, screenshot 위치를 기록한다. 승인 기준이 없으면 임의의 픽셀 일치를 주장하지 않는다.

## 불안정 실패

첫 실패 로그·trace·screenshot·환경을 보존하고 원인을 구분한다.
불안정성 재현이 필요할 때만 횟수·목적을 정해 반복한다.
재시도 후 통과를 첫 시도 성공으로 바꾸지 않는다.
skip/quarantine은 이유·영향·후속 작업을 남기며 필수 수용 기준 통과를 대신하지 않는다.
