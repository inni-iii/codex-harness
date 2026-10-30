---
name: verify-work
description: Verify substantive changes, follow through on discovered defects in the same request, retain regression evidence and assess completion against requirements and affected boundaries.
---

# 요구와 전체 영향에서 검증하기

먼저 무엇을 증명해야 하는지 정한다. 이 스킬과 실행 도구는 프로젝트에 오류가 없음을 보장하지 않는다.

1. 사용자 요구·완료 기준에서 의미 있는 작업 묶음과 예상 결과를 도출하고, 이번 검증 범위·E2E 수행 여부/시점을 먼저 알린다. 구현 설명을 정답지로 삼지 않는다.
2. 변경 경로와 공유 의존성·API·권한·설정의 영향을 찾는다. 영향받는 기존 사용자 흐름도 고른다.
3. `python3 tools/harness/run.py check --plan`으로 선택 명령·이유·미등록 경로를 확인한다.
4. 빠른 관련 검사부터 실행하고 공유 변경·연결 불확실성·제출 범위에 맞춰 통합·스모크·전체 검사로 넓힌다.
5. 종료 코드·실행 수·실패·건너뜀·로그·대상 상태를 확인한다. 수정 후 영향을 받는 검사만 다시 실행한다.
6. 확인한 결함은 즉시 기록하고 재현→수정→회귀 검사를 수행한다. 해당 결과에서 새 문제를 찾으면 같은 요청 안에서 이어서 처리한다.
7. 필요한 검사가 통과하고 발견 사항이 처리된 최종 상태를 다시 검토한 뒤 완료 기준별 근거·미확인·남은 범위를 보고한다.

코드의 실질적인 완료 검토에는 요구 충족과 결함·회귀를 나누어 리뷰한다. 유효한 검사 결과는 재사용한다.

| 조건 | 읽을 자료 |
|---|---|
| 검사 범위·공유 변경·회귀 | [영향과 검사 설계](references/impact.md) |
| 작업 묶음·E2E 시점·사전 검증 범위 안내 | [검증 경계](references/checkpoints.md) |
| 결과·캐시·0개 테스트·커밋 대상 | [근거 판정](references/evidence.md) |
| 코드 완료 검토·명시적인 리뷰 | [요구 충족과 결함 리뷰](references/review.md) |
| 점검/수정을 한 요청 안에서 끝까지 수행·발견한 반례를 회귀로 남길 때 | [검토·보완 반복](references/follow-through.md) |
| task.json을 완료하거나 종류별 증거를 연결 | [완료 기록 검증](references/completion.md) |
| 인증·권한·업로드·외부 응답·비밀값·의존성·실행 설정 변경 | [통합 보안 절차](../security-review/SKILL.md) |
| 사용자 흐름·브라우저 경합·불안정 검사 | [브라우저 검증](references/browser.md) |
| 폼·탐색·인증·프론트/API 연결·공통 UI 동작 변경 | [E2E 작성·실행·분석](../e2e-testing/SKILL.md) |
| CI workflow·필수 검사·runner 조건 | [CI 연결](references/ci.md) |
| 명령 등록·워크플로·실행 옵션 | [검증 도구](../../../tools/harness/docs/verification.md) |
| 여러 세션의 수정·통합 검토 | [세션 격리와 통합 판단](../plan-project/references/collaboration.md) |

`needs_configuration`은 새 앱 검사가 빠졌다는 신호다. 하네스 테스트 통과로 대체하지 않는다.
통과를 위해 요구나 테스트를 낮추지 않는다. 검증을 이유로 임의 staging하지 않는다.
별도 관점은 요구·오류·경계·기존 기능의 대조로 확보한다. 다중 에이전트는 권한이 있을 때만 사용한다.
