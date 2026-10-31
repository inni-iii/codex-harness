# 생명주기 훅과 현재 작업 연결

.codex/hooks.json → scripts/knowledge-hook.py → harness/lifecycle_hooks.py가 공통 진입점이다.
명령 훅은 로컬 Python 표준 라이브러리로 동작한다. 모델·MCP·네트워크·패키지 설치를 호출하지 않는다.
기본 대화 모델을 바꾸거나 UserPromptSubmit 라우팅을 다시 등록하지 않는다.

## 현재 연결

| 이벤트 | 수행 | 한계 |
|---|---|---|
| SessionStart | 검토 지식·연결한 작업·중단/압축 전 기록의 읽기 위치 안내, 정적 변경 감지 기준선 설정 | 작업이나 적용 조건의 진위를 자동 판단하지 않음 |
| PreCompact | 기존 task 경로·상태·해시 기록 | 정렬된 task.json 최대100개를 보는 기존 메타데이터 경로. 세션 소유/전체 대화 복원이 아님 |
| Stop | 연결한 task의 기존 evidence 검토기를 읽기 전용으로 실행하고 인수인계 누락을 알림 | 알림만 반환. 자동 계속 진행·전체 테스트·자동 완료 없음 |
| Interrupt | 연결한 task·notes 해시·마지막 정적 검사 위치를 기록 | 상태 잠금을 기다리지 않음. 중단을 막거나 재시작하지 않음 |
| PostToolUse | 지침·설정·문서/검사기 변경을 감지해 doctor와 필요한 agent-config만 수행 | 정적 점검이며 제품 행동 검사/완료 증거가 아님 |
| PreToolUse | 직접 SSH 변경·scp/rsync 업로드·확인 가능한 SFTP 배치 쓰기를 보조 차단 | 완전한 셸/권한 통제기가 아님 |

SessionStart의 지식 선택/범위·출력은 [지식 계약](knowledge.md)을 따른다.
이전 Interrupt/PreCompact 파일이 있으면 원문 위치를 추가로 안내한다. notes·결정·실패·다음 행동은 작업자가 작성해야 한다.

## 현재 세션의 task 지정

작업 기록을 만드는 의미 있는 작업에서만 연결한다. 짧은 질문마다 task를 만들지 않는다.
명령은 레포 루트에서 실행한다.

```sh
python3 tools/harness/run.py hook bind my-task
python3 tools/harness/run.py hook status
python3 tools/harness/run.py hook clear
```

my-task는 존재하는 열린 작업으로 바꾼다. CODEX_THREAD_ID가 있으면 그 ID의 해시를 사용한다.
없는 클라이언트/일반 터미널에서는 SessionStart가 안내한 24자리 session key를 각 명령의 --session-key에 지정한다.
세션/레포별 하나의 task만 지정하며 최근 파일명이나 다른 미완료 task를 추측해 연결하지 않는다.
완료된 task를 Stop이 확인하면 연결을 해제한다. bind/clear는 task 내용·수용 기준·완료 상태를 변경하지 않는다.

Stop은 [완료 계약](completion.md)의 기존 assess를 재사용한다. 검증/리뷰 근거가 없거나 현재 소스·환경과 다르면
evidence verify로 확인하라는 짧은 알림을 반환한다. notes나 next_action이 없으면 인수인계 확인을 안내한다.
같은 소스/환경과 같은 종류의 알림은 반복 표시하지 않지만 .runtime 근거의 변화도 놓치지 않게 매 Stop에서 다시 판정한다.
훅의 Python/상속 환경이 검사 실행 환경과 다르면 확인이 필요하다는 알림이 생길 수 있다. 실제 완료는 작업 환경의 evidence verify/complete로 판단한다.
소스는 최대2,000개·파일당2 MiB·합계32 MiB 안에서 자동 확인한다. 한도를 넘으면 직접 검증을 안내하며 통과나 완료로 바꾸지 않는다.

## 변경 후 정적 검사

PostToolUse는 Bash/exec_command와 apply_patch/Edit/Write 경로를 관측한다.
SessionStart에서 기준선을 만들고, 이후 .agents/.codex/docs/tools/harness/docs의 md/toml/json,
루트 AGENTS/README·harness.toml과 하네스 검사기/훅 Python 코드의 내용·실행 권한 변화만 고른다.
일반 앱 코드 변경을 이유로 전체 테스트를 실행하지 않는다. 기준선이 없는 첫 PostToolUse에서는 정적 검사를 한 번 수행한다.

doctor는 직접 Python 함수로 호출하고, Codex 설정이나 agent_config 검사기가 바뀌면 기본 agent-config도 호출한다.
구성된 check 명령·설치 스크립트를 실행하지 않는다. 같은 변경은 재사용하고, 검사 중 추가 수정이 생기면 stale로 기록한다.
동시 Post/Stop은 세션 잠금으로 겹친 기록을 피하며 바쁜 콜백은 대기하지 않는다. Interrupt는 별도 파일에 기록한다.
결과에는 검사 종류·상태·건수·변경 경로/해시만 남긴다. 상세 원인은 doctor/security config를 직접 실행해 확인한다.

## 원격 쓰기 보조 차단

PreToolUse는 지원되는 셸 도구의 command/cmd 입력만 분석하며 원격 명령을 실행하지 않는다.
다음과 같은 직접 구문을 인식하면 공식 permissionDecision=deny를 반환한다.

- ssh의 원격 파일 변경·출력 파일 쓰기·일부 Git/패키지/서비스 변경. 일반 -o RemoteCommand와 붙인 옵션, 간단한 shell -c/환경/명령 wrapper도 확인한다.
- scp/rsync의 원격 목적지, rsync의 원격 원본 삭제·명시적인 원격 변경 prefix.
- 레포 안에서 읽을 수 있는 크기 제한된 sftp -b 배치의 put·삭제·이름/권한 변경.

원격 cat/log/목록 조회, 원격→로컬 다운로드, SSH 결과의 **로컬** 출력 리다이렉션은 구분한다.
쓰기 대상이 명시된 업로드/변경 구문은 dry-run 등의 실행 결과를 추측해 허용하지 않는다.
동적 변수/별칭·임의 Python 코드·스크립트·복잡한 셸 문법·읽을 수 없는/stdin SFTP 배치는 완전 분석하지 않는다.
미인식 결과가 읽기 전용이라는 승인은 아니다. 실제 서버 접근은 계속 AGENTS의 사전 확인·읽기 전용 권한을 따라야 한다.
전용 MCP/외부 도구와 일부 도구 경로는 이 셸 matcher를 통과하지 않을 수 있다.

## 저장·신뢰·실제 실행 확인

- .runtime/hook-sessions: 해시 세션 키별 task 연결·변경 감지/알림 상태. state는 최대1 MiB이며 파일은0600이다.
- .runtime/knowledge-events: 압축/중단/종료의 경로·상태·해시. 대화·프롬프트·도구 출력·자동 요약을 저장하지 않는다.
- .runtime/hook-checks: 정적 상태/건수만 기록. 일반 check 보고서처럼 행동 검증 근거로 사용하지 않는다.

콜백 stdin은2 MiB, JSON 깊이는 기존 strict_json 한도다. 원문·명령·외부 오류 본문을 실패 메시지에 복사하지 않는다.
비정상 종료로 세션 lock이 남으면 실제 writer가 끝났는지 확인한 뒤 해당 로컬 lock을 정리한다. 활성 writer의 잠금을 자동 삭제하지 않는다.

현재 정의의 timeout은 SessionStart/PreCompact 5초, Stop 8초, Interrupt/PreToolUse 3초, PostToolUse 10초다.
정의 추가/변경은 Codex CLI /hooks에서 검토·신뢰해야 한다. 전역 신뢰·승인·sandbox를 자동 수정하거나 신뢰 우회 옵션을 사용하지 않는다.
명시적인 deny와 callback 실패는 다르다. 오류·시간 초과·미지원 도구 경로가 모든 실행을 막는다고 가정하지 않는다.
로컬 stdin/반례·회귀 통과와 현재 호스트에서 실제 이벤트가 자동 발생한 것은 별도 증거다.

공식 계약: [Codex Hooks](https://learn.chatgpt.com/docs/hooks). 로컬 프로토콜 검사는 tests/test_lifecycle_hooks.py에 있다.
