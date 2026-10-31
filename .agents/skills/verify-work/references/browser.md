# 브라우저 검증의 범위와 완료 판단

보이는 UI·상호작용·비동기 경합을 바꿀 때 필요한 검증 범위를 정한다.
폼·탐색·인증·API 연결·공통 UI 동작은 의미 있는 사용자 기능 묶음 완성 시 관련 E2E로 확인한다.
작은 편집마다 전체 E2E를 반복하지 않으며 [검증 경계](checkpoints.md)에 따라 수행 범위와 시점을 알린다.

| 확인할 것 | 상세 절차의 정본 |
|---|---|
| 실제 사용자 흐름·API/데이터 경계·대기/locator | [E2E 시나리오](../../e2e-testing/references/scenarios.md) |
| 앱 URL·로컬 서버·runner·데이터·인증·정리 | [E2E 실행 설정](../../e2e-testing/references/setup.md) |
| 화면·뷰포트·키보드·시각 증거 | [화면과 접근성](../../e2e-testing/references/visual.md) |
| trace·실패·retry/flaky·재검증 | [E2E 실패 분석](../../e2e-testing/references/failures.md) |

브라우저 MCP 연결·스크린샷·도구 fixture 성공만으로 실제 사용자 동작이나 서버 권한·저장을 검증했다고 하지 않는다.
실행 수·실패/skip·대상 상태·통과한 실제 경계를 수용 기준과 대조한다. 필수 검사가 미실행이면 해당 기준은 미확인이다.
작성·실행·실패 분석은 [e2e-testing](../../e2e-testing/SKILL.md)이, 최종 요구 충족과 근거 판정은 verify-work가 맡는다.
