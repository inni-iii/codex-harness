# 확인한 연결 문제의 후속

현재 요청은 전체 연결 조사다. 아래 수정/이관은 수행하지 않았으며 완료로 표시하지 않는다.

## F1 — 조사 JSON과 검사 선택 연결

증상: check --full --plan이 needs_configuration. inventory.json/observations.json 두 경로가 uncovered.
영향: 현재 미등록 산출물을 포함한 기본/전체 검사 실행을 막는다. 검사기 자체는 의도대로 누락을 차단한다.
담당 위치: docs/tasks/docker-infra-survey/ 및 tools/harness/harness.toml의 검사/coverage 선언.
다음 행동: 두 파일의 책임과 검사 방식을 정하고 해당 경로만 좁게 등록한다. 임의 docs JSON 전체를 검사 제외하지 않는다.
재확인: 전체 계획에서 uncovered가 사라지고 실제 등록 검사가 실행되는지 확인한다.

## F2 — worktree에 묶인 완료 근거

증상: docker-container-skill의 RED가 .worktrees/docker-containers/.runtime/checks 아래를 참조해 source-only doctor가 실패한다.
영향: 새 복사본/새 환경의 setup·doctor와 이식성 테스트2개를 막는다. 현재 레포 doctor 통과와 구분한다.
담당 위치: docs/tasks/docker-container-skill/task.json·review.json의 근거/검토 계약. 소유 작업과 조정한다.
다음 행동: 실패 원본·로그·해시를 보존하면서 표준 로컬 근거 경로로 옮기고 참조/검토 무결성을 일관되게 갱신한다.
재확인: 현재 doctor와 runtime/worktree 없는 소스 복사본 doctor, 실제 이식성 회귀를 함께 확인한다.
다른 세션 작업을 진행 중 상태로 오인해 임의 삭제하거나 실패 보고서를 통과 보고서로 바꾸지 않는다.

## F3 — 이전 레포에 남은 과거 로컬 근거

증상:11개 작업의63개 .runtime 참조는 현재 레포에서 읽을 수 없다.63개 모두 이전 로컬 레포 원본과 등록 해시가 일치한다.
영향: 과거 결과의 무결성 확인/재사용에 추가 수동 탐색이 필요하다. 현재 동작 실패나 파일 소실로 단정하지 않는다.
담당 위치: 해당 task별 evidence와 로컬 보존/이관 절차. 실제 목록/복구 위치는 .runtime/harness-connection-audit/record-paths.json·recovery-locations.json.
다음 행동: 필요한 원본/로그와 출처를 보존해 이관한다. 과거 보고서의 workspace·시각·소스 해시를 현재 값으로 꾸미지 않는다.
재확인: 당시 근거 무결성과 현재 소스 재검증 여부를 각각 판정한다.
