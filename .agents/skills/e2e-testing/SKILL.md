---
name: e2e-testing
description: Create, run or debug Playwright end-to-end tests for user flows, frontend-to-backend integration, navigation, authentication and shared interactive UI changes.
---

# Playwright E2E 검증

사용자가 실제로 하는 입력·이동·저장·오류 복구를 브라우저에서 확인한다.
Svelte 프론트와 Python API를 연결하는 기능에서는 실제 연결을 통과하는 관련 E2E가 필요하다.
단위/타입 검사 통과나 브라우저 MCP 연결만으로 이 검증을 완료했다고 하지 않는다.

## 실행할 때

- 폼 제출·탐색·인증·권한·API 연결·공통 UI 동작 변경은 의미 있는 사용자 기능 묶음이 완성되는 시점에 관련 E2E로 확인한다. 작은 편집마다 반복하지 않는다.
- 기능은 작성→저장→재조회처럼 사용자가 결과를 얻는 흐름이다. 버튼·파일·컴포넌트별로 지나치게 좁게 잡지 않는다.
- 작업 시작에 검증 범위와 E2E 수행 여부·시점을 알린다. 범위가 바뀌면 실행 전에 이유를 설명한다.
- 기존 프로젝트에 검사가 있으면 수정/재사용한다. 필요한 검사가 없으면 현재 요청 범위 안에서 테스트를 추가하고 로컬 실행 환경을 연결한다.
- 단순 문구·정적 스타일 변경은 실제 화면 확인과 관련 회귀 범위에 맞게 선택한다. 모든 변경에 전체 브라우저 매트릭스를 강제하지 않는다.
- 순수 Python 계산이나 문서만 바꾼 작업은 E2E 적용 여부와 이유를 판단한다.

## 진행

1. 요구 원문·수용 기준·프로젝트 프로필·기존 테스트를 읽고 바뀐 사용자 흐름과 기존 회귀를 고른다.
2. 로컬 서버 시작, 데이터·인증·정리, URL·브라우저·runner 버전을 확인한다.
3. 사용자 행동 → 실제 API/데이터 경계 → 화면 결과를 assert하는 독립 테스트를 작성한다.
4. 관련 시나리오 또는 smoke부터 실행하고 공유 변경·제출 범위에 맞춰 넓힌다.
5. 최초 실패의 로그·trace·screenshot을 읽고 원인을 고친 뒤 영향받는 범위를 재검증한다.
6. 실행 수·실패·skip·retry/flaky·대상 상태·검사한 경계를 보고하고 수용 기준과 대조한다.

| 조건 | 읽을 자료 |
|---|---|
| 새 E2E 시나리오·정상/오류/경계·mock 범위 | [시나리오와 데이터](references/scenarios.md) |
| 기능 묶음·검증 시점·사전 안내 | [검증 경계](../verify-work/references/checkpoints.md) |
| Playwright 설치·서버·설정·하네스 명령 연결 | [실행 설정](references/setup.md) |
| 실제 Playwright 테스트 작성·응답 대기·assertion | [작성 예시](references/writing.md) |
| 느린 응답·불안정 실패·trace·재시도 | [실패 분석](references/failures.md) |
| 화면·뷰포트·키보드·시각 비교 | [화면과 접근성](references/visual.md) |

새 프로젝트에는 [설정 템플릿](assets/playwright.config.cjs)과 [예시 테스트](assets/example.spec.ts)를 실제 앱에 맞게 옮긴다.
예시의 경로·label·payload는 프로젝트 계약으로 교체한다. 템플릿 자체를 앱 검사로 등록하지 않는다.
[레포 실행기](../../../tools/harness/scripts/run-playwright.mjs)는 프로젝트에 설치한 @playwright/test를 실행하고 새 JUnit/실패 artifact 경로를 전달한다.

환경 부족·0개 테스트·전체 skip·미등록 E2E를 통과로 보고하지 않는다.
필수 흐름을 확인하지 못했으면 해당 수용 기준을 미확인으로 남기고 필요한 구성을 보완한다.
스킬은 테스트 작성/수행 절차이며 별도 에이전트나 원격 테스트 권한을 부여하지 않는다.

그래프로 절차·검증·재진입을 관리할 때는 [라우트 계약](routes.toml)에서 현재 작업을 고른다. `flow context <실행ID> --read`로 현재 절차와 허용된 다음 경로만 확인한다. 공통 실행 계약은 [스킬 흐름](../../../tools/harness/docs/skill-flows.md)을 따른다.
