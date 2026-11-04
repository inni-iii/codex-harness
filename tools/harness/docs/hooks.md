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
| PostToolUse | 셸·파일 편집·MCP 뒤 지침/설정 변경의 정적 점검. MCP 응답의 오류 상태와 검토 안내 | 정적 점검·안내이며 내용의 진실성/제품 행동 증거가 아님 |
| PreToolUse | 셸의 직접 원격 쓰기 보조 차단. MCP는 목적·인자·권한 검토 안내 | MCP 인자를 셸 명령으로 해석하거나 자동 허용/차단하지 않음 |

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

PostToolUse는 Bash/exec_command와 apply_patch/Edit/Write, 연결된 mcp__서버__도구 경로를 관측한다.
SessionStart에서 기준선을 만들고, 이후 .agents/.codex/docs/tools/harness/docs의 md/toml/json,
루트 AGENTS/README·harness.toml과 하네스 검사기/훅 Python 코드의 내용·실행 권한 변화만 고른다.
일반 앱 코드 변경을 이유로 전체 테스트를 실행하지 않는다. 기준선이 없는 첫 PostToolUse에서는 정적 검사를 한 번 수행한다.

doctor는 직접 Python 함수로 호출하고, Codex 설정이나 agent_config 검사기가 바뀌면 기본 agent-config도 호출한다.
구성된 check 명령·설치 스크립트를 실행하지 않는다. 같은 변경은 재사용하고, 검사 중 추가 수정이 생기면 stale로 기록한다.
동시 Post/Stop은 세션 잠금으로 겹친 기록을 피하며 바쁜 콜백은 대기하지 않는다. Interrupt는 별도 파일에 기록한다.
결과에는 검사 종류·상태·건수·변경 경로/해시·고정 이유 코드·소요 시간만 남긴다. 상세 원인은 doctor/security config를 직접 실행해 확인한다.

## 실패와 편집 중 점검 구분

| 상태 | 의미와 확인 위치 |
|---|---|
| passed | 수행한 기존 정적 검사 통과. 정상 출력과 검사 횟수는 유지 |
| findings | doctor/agent-config에서 확인할 항목 발견. hook-checks의 결과별 reason_codes·건수를 확인 |
| stale | 검사 중 소스가 바뀜. reason_codes=[source_changed]이며 작업 묶음 종료 때 현재 상태로 확인 |
| callback_failed | 입력 파싱·검사 호출·상태 저장 등 콜백 실행이 실패. hook-errors의 단계·원인 코드를 확인 |

정적 검사 보고서는 기존 .runtime/hook-checks 파일에 elapsed_ms와 제한된 reason_codes만 추가한다.
doctor의 링크·필수 파일·Codex 설정·스킬/flow 등록·lock·문법 발견 사항은 고정 코드로 요약한다.
예외·검사 오류 본문, 검색어·도구 입력/응답·도구 이름·원시 session_id는 복사하지 않는다.
임의 오류 문구를 정확한 원인으로 자동 추정하지 않으며 분류되지 않은 항목은 validation_findings로 남긴다.

콜백 실패에만 .runtime/hook-errors/<해시 세션키>-<허용 이벤트>.json을0600으로 원자 저장한다.
파싱/세션 식별이 안 되면 unidentified/unknown의 고정 이름을 사용한다. 같은 세션/이벤트의 최신 실패 한 건을 교체하며 성공 뒤에도 과거 실패 기록은 남는다.
레코드는 event·stage·code·elapsed_ms·시각·실패 종료 코드만 가진다. stderr에는 단계·코드·상대 기록 경로의 짧은 요약만 전달한다.
예: stage=doctor code=permission_denied는 doctor 호출의 권한 오류이며, doctor가 findings를 반환한 경우와 구분한다.
진단 저장도 실패하면 diagnostic_unavailable로 알리고 원래 비정상 종료를 유지한다. 자동 재시도·검사 추가·모델 호출은 없다.

Python 프로세스 시작/모듈 import 전 실패나 호스트의 강제 종료·timeout은 내부 기록을 남기지 못할 수 있으므로 호스트 오류를 확인한다.
Stop 등에서 이미 제한된 알림으로 처리하는 확인 불가 조건은 callback_failed로 바꾸지 않는다.
이 구분은 오류를 무시하거나 중간 결과를 최종 통과로 바꾸는 기능이 아니다.

## 실패 기록을 다시 쓰는 절차

콜백 오류 기록은 보존만 하지 않는다. 같은 세션의 다음 성공한 PreToolUse/PostToolUse에서
미해결 진단의 단계·코드·경로와 아래 조치 절차를 `hookSpecificOutput.additionalContext`로 모델에 전달한다.
`systemMessage`만으로 모델이 읽었다고 간주하지 않는다. 정적 findings/stale도 모델 맥락으로 전달한다.
SessionStart는 재개 시 미해결을 다시 전달하고 Stop은 UI 알림을 남긴다. Stop이 에이전트를 자동 재실행하지는 않는다.

에이전트는 알림을 받거나 훅 오류를 관측하면 다음 순서로 처리한다.

1. `hook status`로 `pending_failures`의 원문 경로·`failure_sha256`을 확인하고 진단 원문과 관련 task를 읽는다.
2. 원인과 소유권·현재 실행 권한을 확인한다. 현재 요청에서 허용된 수정과 관련 재검증을 이어간다.
3. 실제 재검증 결과를 해당 의미 있는 task의 evidence로 등록하고, 그 근거가 원래 실패의 해결을 확인하는지 판단한다.
4. 아래 `hook resolve`로 정확히 그 실패의 해결을 기록한다. 차단·범위 밖·재검증 불가는 task에 다음 행동을 남기고 미해결로 유지한다.

```sh
python3 tools/harness/run.py hook status
python3 tools/harness/run.py hook resolve PreToolUse --failure-sha256 <현재-64자리-해시> --task my-task --evidence FIX
```

일반 터미널에서는 두 명령에 `--session-key <24자리-키>`를 붙인다. 이벤트 이름 대신 정적 발견 사항은 `StaticCheck`를 사용한다.
FIX는 등록된 artifact/check 증거 ID다. 명령은 증거 무결성과 현재 실패 해시를 확인하며, 실패 기록 자체는 해결 근거로 거부한다.
이 기계 검사는 근거의 의미까지 보증하지 않는다. 에이전트가 원래 실패 조건의 재검증을 확인해야 한다.
기록을 삭제하거나 임의로 해결 표시해 경고를 숨기지 않는다.

동일한 미해결 콜백의 이벤트·단계·코드는 도구마다 반복 주입하지 않는다. 재개 시에는 다시 안내한다.
해결은 실패 파일의 해시에 묶이므로 해결 후 같은 원인으로 새 실패가 나도 다시 미해결이 된다.
정적 점검은 기존 실제 재검사의 passed가 최신 보고서에 기록되면 미해결에서 빠진다. 진단 파일의 존재나 일반 도구 성공을 해결로 추정하지 않는다.

정상 경로에는 최대7개 고정 진단 경로의 조회와 존재하는 작은 보고서 읽기만 더한다. 진단은 파일당8 KiB,
수신/해결 기록은16 KiB로 제한하고 원문 입력·외부 응답·임의 로그 필드를 맥락에 복사하지 않는다.
추가 모델 호출·자동 수정 프로세스·자동 재시도·doctor/check 실행은 없다. 활성 에이전트가 이 절차를 수행한다.
수신 기록 저장 실패 시 알림은 전달하지만 다시 나올 수 있다. 잠금 경합 시 다음 콜백으로 미루고 실패 기록을 유지한다.

세션을 식별하지 못한 `unidentified` 기록을 임의의 세션에 연결하지 않는다. 시작/import/timeout 실패나
기록 읽기 불가는 호스트 오류와 `hook status`의 `recovery_unavailable`도 확인한다.
호스트가 도구 이벤트를 발생시키지 않는 내장 검색 경로는 이 reader가 실행되지 않으므로 관측한 오류에 위 절차를 직접 적용한다.
다른 세션은 소유 task/인수인계를 명시해서 이어가며 타 세션 진단을 자동 수집하지 않는다.

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
MCP는 별도 분기로 처리하며 셸 가드에 입력하지 않는다. 일부 도구 경로는 호스트의 도구 훅 자체를 통과하지 않을 수 있다.

## MCP 호출과 내장 웹검색

기존 연결의 mcp__서버__도구 이름을 패턴으로 인식한다. 훅을 위해 새 검색 MCP를 등록할 필요는 없다.
새 서버 설치/등록·연결은 별도 설정이며 훅이 연결되지 않은 서버를 시작하지 않는다.

Pre는 목적·대상·인자·민감정보 전송·현재 권한을 확인하라는 고정 안내를 반환한다.
Post는 비신뢰 응답의 오류·형식·자원·원문/날짜를 검토하도록 안내하고, 직접 MCP 결과의 isError=true·비정상 isError 타입·응답 누락은 별도 알림을 반환한다.
임의 도구별 schema·응답 본문의 진실성·인용 지지 여부를 자동 검증하지 않는다. 응답 래퍼/서버별 오류는 에이전트가 실제 결과에서 확인한다.
결과를 차단·수정하거나 오류 응답의 재시도를 자동 실행하지 않으며 원문 입력·응답·도구 이름을 메시지나 상태로 복사하지 않는다.
MCP 뒤 로컬 watched 변경에도 기존 정적 점검을 적용한다. 다른 콜백이 잠금을 가진 경우 정적 기록은 건너뛰어도 MCP 안내는 반환한다.

내장 WebSearch는 공식적으로 PreToolUse/PostToolUse 대상이 아니므로 matcher를 넓혀도 자동 이벤트가 생기지 않는다.
이 경로는 [검색 전후 확인](../../../.agents/skills/research/references/web-search.md)을 현재 에이전트가 수행한다.
MCP 안내·로컬 stdin 검사·내장 검색 지침의 존재와 실제 호스트 이벤트/의미 검증의 수행은 구분한다.
MCP 이미지·과대 응답도 기존 stdin2MiB/깊이 한도를 적용한다. 한도 초과는 검증 성공이 아니며 호스트의 콜백 실패 정책을 따른다.

## 저장·신뢰·실제 실행 확인

- .runtime/hook-sessions: 해시 세션 키별 task 연결·변경 감지/알림 상태. state는 최대1 MiB이며 파일은0600이다.
- .runtime/knowledge-events: 압축/중단/종료의 경로·상태·해시. 대화·프롬프트·도구 출력·자동 요약을 저장하지 않는다.
- .runtime/hook-receipts: 세션별 알림 토큰과 해결한 실패 해시·task/증거 참조. 원래 실패 기록은 보존한다.
- .runtime/hook-checks: 정적 상태/건수만 기록. 일반 check 보고서처럼 행동 검증 근거로 사용하지 않는다.

콜백 stdin은2 MiB, JSON 깊이는 기존 strict_json 한도다. 원문·명령·외부 오류 본문을 실패 메시지에 복사하지 않는다.
비정상 종료로 세션 lock이 남으면 실제 writer가 끝났는지 확인한 뒤 해당 로컬 lock을 정리한다. 활성 writer의 잠금을 자동 삭제하지 않는다.

현재 정의의 timeout은 SessionStart/PreCompact 5초, Stop 8초, Interrupt/PreToolUse 3초, PostToolUse 10초다.
정의 추가/변경은 Codex CLI /hooks에서 검토·신뢰해야 한다. 전역 신뢰·승인·sandbox를 자동 수정하거나 신뢰 우회 옵션을 사용하지 않는다.
명시적인 deny와 callback 실패는 다르다. 오류·시간 초과·미지원 도구 경로가 모든 실행을 막는다고 가정하지 않는다.
로컬 stdin/반례·회귀 통과와 현재 호스트에서 실제 이벤트가 자동 발생한 것은 별도 증거다.

공식 계약: [Codex Hooks](https://learn.chatgpt.com/docs/hooks). 로컬 프로토콜 검사는 tests/test_lifecycle_hooks.py에 있다.
