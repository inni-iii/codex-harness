# 생명주기 훅 구현과 검증 범위

2026-10-31. Stop 보강·Interrupt·PostToolUse·PreToolUse를 기존 SessionStart/PreCompact와 함께 연결했다.
실제 사용 계약은 [훅 안내](../../../tools/harness/docs/hooks.md), 등록 정의는 [.codex/hooks.json](../../../.codex/hooks.json)이 정본이다.
UserPromptSubmit은 미등록이며 기본 모델·라우팅 의무·전역 신뢰·권한을 바꾸지 않았다.

## 요구와 동작

- A1: hook bind로 연결한 task만 읽는다. Stop은 기존 evidence.assess로 매번 현재 근거를 확인한다. 동일 알림을 재사용하며 계속 작업하라는 decision이나 자동 완료를 반환하지 않는다.
- A2: Interrupt는 상태 잠금과 독립적인 파일에 task/notes의 경로·상태·해시와 마지막 정적 검사 위치를 남긴다. SessionStart에서 원문 위치를 안내한다. 프롬프트·대화·도구 입출력·자동 요약을 저장하지 않는다.
- A3: 지침·설정·문서·하네스 Python 변경만 감지한다. doctor와 필요한 agent-config를 직접 호출하며 동일 변경은 재사용한다. 검사 중 추가 수정은 stale이다. 등록 검사 명령·모델·네트워크·설치·앱 테스트를 자동 실행하지 않는다.
- A4: 직접 SSH 쓰기·scp/rsync 업로드·확인 가능한 로컬 SFTP 배치 변경은 공식 permissionDecision=deny로 반환한다. 원격 읽기·다운로드·SSH 결과의 로컬 리다이렉션을 구분한다. 모든 반례는 문자열/합성 로컬 파일만 사용하며 원격 명령을 실행하지 않았다.
- A5: 여섯 이벤트 등록과 CLI bind/status/clear, 읽을 조건·스킬 참조·문서 지도·보안 한계를 함께 갱신했다. 훅의 상세 계약은 hooks.md 한 곳에서 관리한다.

## 실제 확인과 회귀 근거

기존 연결 검사는34개, 보완 후 관련 검사는39개 통과했다. 이후 등록된 전체 검사로 최종 소스 사본을 검증하며 task의 check 근거에서 실제 결과·로그·테스트 수를 확인한다.
수정 전 전체 보고서 `.runtime/lifecycle-boundaries-red/c8ae4be5edd3492e8bcb7a7624a30492/report.json`은 격리 worktree에 보존한다. 최종 테스트 파일을 변경하지 않고 수정 전/후의 같은 사례를 대조한다.

- F1: 붙인 SSH 옵션·rsync 원격 prefix·SFTP 오류무시 접두사를 놓치거나 로컬 리다이렉션을 혼동했다. 옵션 값·외부 리다이렉션·원격 명령 문맥을 구분하도록 수정했다.
- F2: Stop의 소스 캐시가 runtime 증거 변경을 놓쳤다. 매 Stop마다 기존 검토기를 읽고 알림 표시만 중복 방지한다. 비객체 task는 원문 없는 확인 불가 알림으로 처리한다.
- F3: 다른 콜백이 상태 잠금을 소유하면 Interrupt 기록이 사라졌다. 마지막 원자 상태를 읽고 별도 중단 파일을 쓰도록 분리했다.

실제 stdin 스모크는 임시 레포 사본에서 SessionStart → README 변경 → PostToolUse의 실제 doctor, 동일 변경 재사용, Codex 설정 변경 후 실제 doctor+agent-config를 확인했다. PreToolUse 읽기/쓰기 분기와 Interrupt의 합성 프롬프트 미저장도 확인했다. 이 스모크는 `.runtime/lifecycle-live-smoke.py`로 수행했고 제품 UI 변경은 없어 브라우저 E2E는 비적용이다.

## 한계

동일 작성자의 자체 검토이며 독립 보안 평가가 아니다. 셸 분류기는 동적 스크립트·별칭·임의 코드·미관측 MCP 경로까지 통제하지 않는다. 오류/시간 초과 시 완전한 차단을 보장하지 않는다. AGENTS의 원격 읽기 전용 규칙과 호스트 권한이 계속 필요하다.
현재 호스트에서 네이티브 이벤트가 자동 발생하는지와 변경된 정의의 신뢰 승인은 미확인이다. 로컬 stdin 계약 통과를 자동 활성화 완료로 확대하지 않는다. `/hooks`의 현재 정의 검토는 사용자가 해당 훅을 사용할 때 수행한다.
