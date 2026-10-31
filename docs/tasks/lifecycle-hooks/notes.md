# 생명주기 훅 구현 기록

2026-10-31 사용자 승인: Stop 보강·Interrupt·PostToolUse·PreToolUse 모두 적용. 기본 모델/라우팅 의무는 복원하지 않는다.

## 경계와 검증 계획

base d75b6aa에서 .worktrees/lifecycle-hooks로 격리했다. 모델·네트워크·원격 명령 없이 순수 입력 분류/메타데이터/기존 정적 검증을 연결한다. 앱 UI 변경이 없어 브라우저 E2E는 비적용. 기존 학습 훅·조건/증거·완료 계약과 라우팅 미등록 상태를 유지한다. native 신뢰와 실제 호스트 이벤트는 로컬 stdin 계약 검사와 구분한다.

세션당 task 하나를 명시적으로 연결하며, 다른 미완료 task를 자동 선택하지 않는다. Stop은 기존 검토기를 읽기 전용으로 사용하고 알림만 반환한다. Interrupt는 상태/경로/해시만 저장하고 재개 안내에 연결한다. Post는 watched 변경/캐시·동시 실행을 확인하며 임의 check 명령을 실행하지 않는다. Pre는 명백한 직접 원격 변경만 보조 차단하고 실제 권한 경계를 대체하지 않는다.

## 발견과 회귀

- F1: 추가 옵션 형태에서 ssh -oRemoteCommand=touch, rsync --rsync-path의 원격 mkdir, 공백/오류무시 접두사가 있는 sftp 배치 put을 놓친다. 원격 명령을 실행하지 않고 문자열/로컬 합성 배치로 재현한다.
- F2: Stop의 소스 기반 캐시가 .runtime 근거 변경을 보지 못하면 기존 검토기의 새 오류를 확인하지 않는다. 로컬 원문 편집 없이 근거의 상태가 바뀐 경우도 다시 판정해야 하며 같은 알림의 중복 표시는 피한다.

초기 관련33개 통과 로그는 .runtime/lifecycle-initial-tests.log. 위 반례를 추가해 수정 전 실제 실패를 보존한 뒤 보완한다.

- F1 추가 반례: ssh의 로컬 출력 리다이렉션을 원격 쓰기로 혼동하거나, 호스트 앞 리다이렉션으로 실제 원격 쓰기를 놓친다. 로컬/원격 셸 문맥을 구분한다.
- F2 추가 반례: 바인딩 후 task가 배열 JSON으로 바뀌면 AttributeError가 발생할 수 있다. 검증 불가를 원문 없는 알림으로 반환한다.
- F3: 다른 Post/Stop 콜백이 세션 잠금을 소유하는 동안 Interrupt가 기록을 생략한다. 중단 전용 파일은 상태 잠금을 기다리지 않고 마지막 원자 저장 상태에서 작성해야 한다.
초기 연결 검사 수는33이 아닌34개였다. 새 경계 반례와 기존 검사 파일은 마지막 수정 전 보고서 기준으로 고정한다.

## 최종 검증과 통합

원래 HEAD와 파일별 원문을 대조해 이번 변경24개만 main 작업 트리에 반영했다. 별도 진행 중인 docs/tasks/skills-consolidation은 변경하지 않았다. commit/push/자동 merge는 하지 않았다.

현재 레포에서 check --snapshot --full 보고서 .runtime/check-snapshots/dc63968b685d4908aeb70dd001f52195/checks/06e44aa3122749d78427651067944e26/report.json: passed, live_source_changed=false. doctor/agent-config/secret-patterns와 Python332개 실행, failed0, skipped1. 건너뛴 항목은 기존 process-group signal 권한이 없는 환경의 하위 사례다. 훅별 관련39개 통과와 실제 stdin 정적 점검 스모크도 확인했다.

F1/F2/F3 회귀는 같은 test_lifecycle_hooks.py 해시의 실제 RED/GREEN과 연결했다. 결과 정본 result.md, 기준별 자체 검토 review.json. evidence verify가 현재 소스·환경·로그·회귀와 기준 연결을 통과했다. 네이티브 이벤트 자동 발생/신뢰 승인은 미확인이고 글로벌 설정을 바꾸지 않았다.
