---
name: verify-work
description: Verify substantive changes, follow through on discovered defects in the same request, retain regression evidence and assess completion against requirements and affected boundaries.
---

# 요구와 전체 영향에서 검증하기

먼저 무엇을 증명해야 하는지 정한다. 이 스킬과 실행 도구는 프로젝트에 오류가 없음을 보장하지 않는다.

1. 사용자 요구·완료 기준에서 의미 있는 작업 묶음과 예상 결과를 도출하고, 이번 검증 범위·E2E 수행 여부/시점을 먼저 알린다. 구현 설명을 정답지로 삼지 않는다. 상위 계획이 있으면 관련 요구·성공 조건과 이번 작업이 해결할 갭을 확인한다.
2. 변경 경로와 공유 의존성·API·권한·설정의 영향을 찾는다. 영향받는 기존 사용자 흐름도 고른다.
3. `python3 tools/harness/run.py check --plan`으로 선택 명령·이유·미등록 경로를 확인한다.
4. 빠른 관련 검사부터 실행하고 공유 변경·연결 불확실성·제출 범위에 맞춰 통합·스모크·전체 검사로 넓힌다.
5. 종료 코드·실행 수·실패·건너뜀·로그·대상 상태를 확인한다. 수정 후 영향을 받는 검사만 다시 실행한다.
6. 확인한 결함은 즉시 기록하고 재현→수정→회귀 검사를 수행한다. 해당 결과에서 새 문제를 찾으면 같은 요청 안에서 이어서 처리한다.
7. 필요한 검사가 통과하고 발견 사항이 처리된 최종 상태를 다시 검토한 뒤 완료 기준별 근거·미확인·남은 범위를 보고한다. 상위 계획이 있으면 [프로젝트 진행](../plan-project/references/project-lifecycle.md)에 따라 관련 갭의 전후 변화·근거를 연결한다. 작업 완료를 마일스톤 전체 달성으로 확대하지 않는다.

코드의 실질적인 완료 검토에는 요구 충족과 결함·회귀를 나누어 리뷰한다. 유효한 검사 결과는 재사용한다.

## 필요한 상세 자료만 읽는다

작은 문서 편집·검토는 위 공통 흐름과 [문서 검증](../docs-maintenance/references/validation.md)으로 범위를 정한다.
코드·실행 설정·계약을 바꾸면 관련 경로를, 명시적 코드 리뷰에는 `code-review`, 상세 코드 검증에는 `code-verification` 주제를 추가한다.
실제 결함을 발견하면 문서 작업이라도 `regression`/`repair-loop`로 반복 절차를 읽고, task를 닫을 때는 `completion`/`task-evidence`로 증거 계약을 확인한다.
가벼운 작업에서 상세 자료를 생략해도 요구 대조·검증 범위 안내·실제 결과 확인·발견 처리·최종 재검토는 수행한다.
경로나 주제로 드러나지 않은 위험을 찾으면 필요한 원문을 추가한다. 선택 결과가 영향 분석을 대신하지 않는다.

| 조건 | 읽을 자료 |
|---|---|
| 검사 범위·공유 변경·회귀 | [영향과 검사 설계](references/impact.md) |
| 작업 묶음·E2E 시점·사전 검증 범위 안내 | [검증 경계](references/checkpoints.md) |
| 결과·캐시·0개 테스트·커밋 대상 | [근거 판정](references/evidence.md) |
| 구현 전 의도·경계·설계/정렬 근거와 R/O·수용조건 확인 | [설계와 정렬](../plan-project/references/reasons-canvas.md) |
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

그래프로 절차·검증·재진입을 관리할 때는 [라우트 계약](routes.toml)에서 현재 작업을 고른다. `flow context <실행ID> --read`로 현재 절차와 허용된 다음 경로만 확인한다. 공통 실행 계약은 [스킬 흐름](../../../tools/harness/docs/skill-flows.md)을 따른다.
