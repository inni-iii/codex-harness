# 작업 기록

중요한 발견·실패·정정과 그 근거를 날짜와 함께 기록한다.
공통 규칙으로 만들 후보는 적용 조건·제외 조건·재현/회귀 근거를 함께 남긴다.

## 검증 계획

- 사용자 결과 기준의 의미 있는 작업 묶음:
- 이번 검증 범위·checkpoint와 사용자에게 알린 내용:
- E2E 수행 여부·시점·사유와 미룬 검사:
- 격리 위치·기준 상태·통합 시 함께 유지할 요구:

## 확인한 결함과 회귀

실제 결함을 확인하면 ID·증상·재현 입력·기대 결과·근거를 즉시 적는다. 추측과 환경 오류는 구분한다.
수정 전 실패·수정 후 통과·테스트/시나리오 위치·검사 수집 조건·미실행 이유를 보존한다.
마지막 수정 뒤의 재검토를 남기고 review.json의 verification.findings/rounds에 연결한다.

## 인수인계

- 목표·범위·현재 상태와 이어서 읽을 자료:
- 확정 결정·이유·미결정:
- 수용 기준별 실제 명령·cwd·대상 상태·결과·근거 위치:
- 실패/탈락한 방법·당시 조건·재검토 조건:
- 남은 문제·환경 전제:
- 다음 한 행동(파일/함수/명령과 관측할 결과):

다른 노트북에 없는 로컬 로그는 재현 명령도 남긴다. 비밀값·개인 경로는 기록하지 않는다.

## F1: route procedure ownership
Directly registering the planning reference as a verification route document violates the existing route-owner contract. Actual doctor and the request-only route regression fail with route procedures belong to their owning skill. Keep the primary reference in planning routes; verification consumes its own acceptance procedure, which links to the owner. Preserve before/after evidence and recheck real route reads.

## Final verification
Current checkout retained per explicit user instruction. The final registered check passed: 508 Python tests, zero failures, one sandbox group-signal subcase skipped. Doctor, config and secret checks passed. The 4 new scoped-selection/route/resume cases passed. F1 is fixed with unchanged-test isolated red and current green evidence. Semantic scenarios are self-review, not independent assessment. Hook status reports passed with no pending failure; a later successful record superseded the transient static finding. Flow finished; next action is use the generic procedure in an actual project.

## Concurrent source refresh
Completion verification rejected the first passing report after another session changed shared execution/evidence modules and related guidance. Preserve that run as historical artifact GREEN. A fresh final check uses the current source snapshot. Do not weaken criteria or alter the other session changes.

Latest snapshot check LATEST passed after concurrent changes: 520 tests, zero failures, one sandbox-related skip. Prior finished flow is historical after shared source edits; project-explanation-final records the current verification. Source-linked semantic scenario review is unchanged.

F2: a failed registration was followed by an unguarded metadata edit; actual unknown-ID verification error was observed and corrected. Atomic evidence import now guards all final registrations. Only the shared task map changed after the full 520-test snapshot. CURRENT verifies current map, static/config/secret checks and all 4 integration cases; unaffected full-code results are retained historically.
