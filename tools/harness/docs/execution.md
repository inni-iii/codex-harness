# 선택적 모델 추천과 실행

2026-10-31 현재 결정: 라우팅 의무를 해제하고 일반 대화창의 자동 추천·인수인계를 보류했다.
기본 작업은 현재 대화창의 모델로 수행한다. 필요할 때 `catalog`/`route`로 모델·추론 강도 추천만 받을 수 있다.
`run`/`chat`은 별도 모델 실행 방식을 명시적으로 선택할 때 사용하는 도구이며 기본 작업의 선행 단계가 아니다.
이 문서는 보존된 도구의 실행 계약과 미검증 범위를 설명한다.

## 명시적으로 선택해 사용하기

Python 3.11 이상과 설치·로그인된 Codex CLI가 필요하다. 명령은 레포 루트 기준이다.
작업 위치는 현재 디렉터리가 기본이며 다른 위치는 `--cwd`로 지정한다.

```sh
python3 tools/harness/run.py run --sandbox workspace-write "실제 수행할 작업"
python3 tools/harness/run.py run --sandbox read-only "실제 검토할 내용"
python3 tools/harness/run.py chat --sandbox workspace-write
make work
```

권한 옵션을 생략하면 기존 Codex 설정을 사용한다. `codex exec`의 기본 sandbox는 read-only이므로
편집 작업에는 현재 호스트에서 허용된 workspace-write를 명시한다. 런처는 인증·승인 정책·rules·도구 설정을
덮어쓰지 않으며 danger-full-access·승인 우회·훅 신뢰 우회 옵션을 제공하지 않는다.
현재 호스트가 read-only이면 workspace-write로 넘기지 않는다. 원격 셸은 계속 읽기 전용이다.

`run`은 요청→지원 목록→규칙/분류 모델→정책→선택 모델 실행을 자동 수행한다.
일반 요청은 별도 분류 모델 설정 없이 지원 목록과 정책의 명확한 소규모 작업 기준에서 분류용 조합을 고른다.
분류용 조합과 실제 작업용 조합은 별개다. `--classifier-model`/`--classifier-effort`로 분류 설정을,
`--model`/`--effort`로 지원 검사를 거친 작업 설정을 직접 지정할 수 있다.
실제 분류·작업 실행에는 사용량이 발생한다. 개인 설정의 작업 모델을 고정 fallback으로 사용하지 않는다.
기존 `route`의 명시적 분류 설정·`--rules-only` 동작은 [추천기 안내](usage.md)를 유지한다.

`run -`는 stdin에서 요청을 읽는다. 지정한 맥락 파일은 한 번 읽고 같은 바이트를 분류기와 작업자에게 전달한다.
원문은 argv에 넣지 않는다. 작업 모델의 입력에는 원문 요청·출처가 붙은 맥락·이미 라우팅한 결정 ID가 포함된다.
불충분한 맥락을 임의로 채우거나 성공을 위해 요청을 다시 쓰지 않는다.

```sh
python3 tools/harness/run.py run --sandbox workspace-write \
  --context-file docs/projects/demo/brief.md "이 프로젝트의 첫 기능을 구현해줘"
```

위 프로젝트 경로는 예시다. 실제 존재하는 자료로 바꾼다. `chat`은 매 줄을 독립 요청으로 다시 라우팅하며
이전 요청과 실제 답변을 다음 분류기·작업자의 맥락으로 전달한다. 각 작업자는 새 Codex 프로세스다.
도구 실행 로그·숨은 추론·원래 TUI 세션 전체를 복제하는 것은 아니다. `/quit` 종료, `/clear`는 대화 맥락을 초기화한다.
대화 맥락은 이 프로세스의 메모리에만 유지한다. 재시작 시 필요한 인수인계 파일을 직접 제공한다.
요청과 맥락의 합계는 1 MiB 이하다. 넘으면 자동으로 잘라내지 않고 인수인계를 요구한다.

## 일반 Codex 대화창의 자동 호출

**현재 보류 상태다.** 레포 `.codex/hooks.json`에서 라우터의 `UserPromptSubmit` 등록을 제거했다.
자동 추천·인수인계는 기본 동작이 아니며 라우터 훅의 등록·신뢰 승인을 요구하지 않는다.
`.codex/config.toml`의 hooks 기능은 기존 SessionStart·PreCompact·Stop 학습 훅 때문에 켜 둔다.

`route_prompt.py`와 `routing/hooks.py`는 등록하지 않은 보관 코드다. 명시적으로 호출한 경우
요청을 분류하고 한 번 사용할 `run --request-id <ID>` 명령을 호스트에 전달하도록 구현돼 있다.
이 구현은 현재 대화창의 모델을 직접 교체하지 않으며, 호스트가 인수인계 지침을 수행해야 한다.
실제 대화창 연결과 모델 실행을 검증하기 전에는 자동 호출을 재도입하지 않는다.
기존 실행 중 클라이언트가 이전 설정을 캐시했다면 레포 설정을 다시 읽거나 새 세션에서 현재 설정을 확인한다.

아래 대기 요청·transcript 처리는 보관된 인수인계 코드의 계약이며 일반 작업의 필수 절차가 아니다.

훅에서 준비한 요청은 5분 안에 같은 작업 경로에서 소비해야 한다. 실행에는 현재 호스트와 같은 `--sandbox`를
반드시 지정한다. 다른 요청·맥락·모델 옵션과 섞지 않는다. 동시에 두 번 실행하면 한 번만 claim할 수 있다.
오류·중단 이후에는 ID를 재사용하지 않는다. 이미 파일이나 외부 상태가 바뀌었을 수 있기 때문이다.
이전 요청 파일은 실행을 claim할 때 삭제한다. 사용하지 않은 대기 요청에는 원문이 남으므로 개인 로컬 자료로 관리한다.
체크섬·정책 해시·만료 검사는 입력의 일관성을 확인하며, 파일 소유자에 대한 보안 인증이나 실행 권한 부여가 아니다.

훅은 Codex가 제공한 현재 대화 transcript의 user/assistant 메시지를 맥락으로 읽는다.
현재 지원하는 저장 형식은 Codex response_item message다. `.codex/sessions`·`archived_sessions` 밖의 경로,
과대 자료·파싱 오류는 차단하고 명시적인 인수인계를 요구한다. transcript 형식은 제품의 안정 계약이 아니므로
호스트 변경 시 재검증한다. 과거 Claude·Codex 전체 기록 확인 지침을 이 단일 transcript로 대체하지 않는다.

이미 라우팅된 작업용 프로세스는 환경의 결정 ID와 running 기록을 확인하고 훅의 재귀 라우팅을 생략한다.
같은 작업에서 다시 `run`/`chat`을 호출하면 실행기가 차단한다. 이 표시는 권한 승인이 아니다.

## 결과와 실패 처리

`run`은 stdout에 JSON 결과와 `response`, stderr에 선택 모델·effort·결정 ID를 출력한다.
`chat`은 stdout에 답변, stderr에 선택·실행 메타데이터를 출력한다.

| 상태/필드 | 의미 |
| --- | --- |
| ready | 추천만 완료. `route`의 상태이며 실행 성공이 아님 |
| executed | 작업 프로세스가 종료 코드 0·turn.completed·답변을 반환함. 제품 수용과 별개 |
| execution_failed | 실행·출력·관측 설정 불일치·시간/출력 한도 등의 실패 |
| execution_blocked | 입력·맥락·대기 요청·정책·목록 검사에서 실행 차단 |
| worker_started | Codex 프로세스 생성 여부 |
| task_executed | JSON 이벤트에서 turn.started를 관측했는지 |
| observed_configuration | 해당 작업 thread의 turn_context에서 읽은 모델·effort, 없으면 null |
| observation_status | verified_configuration 또는 unverified. 추천을 관측값으로 복사하지 않음 |
| backend_model_verified | 항상 false. CLI 설정 관측은 서버 내부 실제 모델의 증명이 아님 |
| usage | CLI가 보고한 토큰 수, 없으면 null. 청구 비용으로 환산하지 않음 |
| quality | 항상 unrated. 성공 종료를 요구 충족·최적성으로 표현하지 않음 |

종료 코드 0은 executed, 그 외는 2이며 입력 대기 중 사용자 중단은 130이다.
실행 중 중단은 프로세스 정리 후 execution_failed/interrupted로 기록한다.
실행 중 실패에 자동 모델 교체·재시도는 없다. 부분 수행된 상태를 확인하고 다음 요청을 정한다.
기본 작업 시간 한도는 1800초, stdout+stderr 총량은 8 MiB다. `--task-timeout`·`--max-output-bytes`로 조정한다.
출력 한도는 1 KiB~64 MiB다. timeout/초과/중단 시 프로세스 그룹을 정리하며, 운영체제가 그룹 정리를 거부하면
cleanup_error도 기록한다. 프로세스 그룹 처리는 sandbox가 아니며 모든 OS에서 자원 정리를 보증하지 않는다.

기록은 작업 경로의 `.runtime/routing/<결정 ID>/run.json`에 권한 0600으로 저장한다.
추천·분류 범주·프로세스 종료·사용량·관측 설정만 남기고 원문·자유 서술 분류 결과·stderr·답변은 저장하지 않는다.
대기 요청 `request.json`에는 실행에 필요한 원문이 별도로 들어가며 0600이다. Git 제외를 비밀 보호의 증명으로 삼지 않는다.
Codex 자체의 세션 보존은 기존 Codex 설정을 따른다. 민감한 원문이나 결과를 문서·공유 로그에 복사하지 않는다.

## 검증 범위와 현재 한계

자동 검사는 대체 CLI 프로세스로 분류→선택→작업 파일 변경, 같은 맥락 전달, 매 입력 재라우팅,
실패·시간·출력 한도·재귀 차단·대기 요청 한 번 소비·관측 설정 불일치를 다룬다.
대체 CLI는 실제 모델의 분류 정확도·작업 품질이나 실제 훅 활성화를 증명하지 않는다.
2026-10-31 이 환경의 실제 CLI 0.166.0에서는 지원 목록 조회를 확인했으나 작업 프로세스가
`failed to initialize in-process app-server client: Operation not permitted`로 초기화되지 않았다.
실제 분류/편집·대화창 훅 인수인계는 라이브 미검증이다. 권한 우회나 전역 신뢰 변경은 하지 않았다.

```sh
python3 -m unittest discover -s tools/harness/tests -p 'test_routing*.py' -v
python3 -m unittest discover -s tools/harness/tests -p test_routed_execution.py -v
python3 tools/harness/run.py doctor
```

공식 근거: [비대화형 실행](https://learn.chatgpt.com/docs/non-interactive-mode),
[UserPromptSubmit와 훅 신뢰](https://learn.chatgpt.com/docs/hooks). 문서와 설치 CLI에서 확인한 범위를 구분한다.
