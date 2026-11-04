# 스킬 라우트와 조건부 작업 흐름

`flow`는 현재 대화의 에이전트가 수행하는 절차의 위치와 허용된 이동을 관리한다.
노드는 `스킬:라우트`, 엣지는 `call` 또는 `transition`과 조건이다. 모델 선택 `route` 명령과 별개다.
라우트 선택 → 입력 확인 → 절차 → 결과 검증 → 복귀/전이/재진입/종료를 기록한다.
명령이 성공했다는 것은 해당 상태 갱신이 허용됐다는 뜻이다. 응답의 `flow_status`와 `stale`을 함께 확인한다.

## 배치와 책임

- 각 스킬의 `routes.toml`: 적용 조건·필수 입력·현재 원문·순서 있는 절차·검증 기준·필수 증거 유형·호출·종료 조건.
- [.agents/skill-flow.toml](../../../.agents/skill-flow.toml): 허용된 경로와 조건. 명령/코드/표현식을 실행하는 필드는 없다.
- [flow_catalog.py](../harness/flow_catalog.py): 계약·경로·단일 소유권·종료 경로 검증.
- [skill_flows.py](../harness/skill_flows.py): 지속 상태·호출 스택·조건 판정·검증 근거·반복 제한.
- `.runtime/skill-flows/<실행ID>.json`: 현재 위치·완료 절차·근거 ID/해시·호출/복귀·질문·이동 기록. Git에서 제외한다.
- 기존 task/evidence: 목표·범위·수용 기준·실제 증거·완료의 정본. flow는 task를 자동 완료하거나 기준/리뷰를 복제하지 않는다.

자동 모델·셸·테스트·외부 도구 실행기나 백그라운드 에이전트가 아니다. 에이전트가 현재 절차를 읽고 실제 작업·검사를 수행한 뒤 증거와 이동을 기록한다.
그래프의 허용 경로는 실행 권한을 부여하지 않는다. 읽기 요청·설계만의 요청·원격 서버 읽기 전용 경계를 그대로 지킨다.

## 시작과 현재 절차

명령은 레포 루트에서 프로젝트의 정상 Python으로 실행한다. 예시의 이름·증거 ID는 실제 작업 것으로 바꾼다.
먼저 task의 목표·범위·수용 기준별 확인 방법을 정한다. 방법·범위를 도중에 바꾸면 계약이 바뀌므로 의도적인 재시작이 필요하다.

```sh
python3 tools/harness/run.py flow catalog
python3 tools/harness/run.py flow catalog --node plan-project:plan
python3 tools/harness/run.py flow start my-flow --task my-task --node plan-project:plan
python3 tools/harness/run.py flow context my-flow --read
python3 tools/harness/run.py flow status my-flow
```

코드 구현/수정과 구현 후 `verify-work:check`에는 design/alignment가 필요하다. 기존 결과물의 기본 검증은 request-only `verify-work:inspect`로 시작할 수 있고, 실제 수리 호출에는 기존 준비 입력을 연결한다. [REASONS 준비 검사](reasons.md)에서 현재 설계·검토·선택 O·범위를 확인한다. 아래의 일반 입력 예는 각 라우트의 실제 입력으로 바꾼다.

필수 입력 `request`는 연결한 task 계약으로 자동 묶는다. 추가 입력을 요구하는 사용자 정의 라우트는
`--input design=DESIGN`처럼 **이미 task에 등록한 증거 ID**로 전달한다. 누락·중복·알 수 없는 입력·request 덮어쓰기는 거부한다.
대상 라우트로 이동할 때 필요한 추가 입력도 `move --input 이름=증거ID`로 명시한다.

`flow context`는 현재 라우트의 SKILL/절차와 출구 메타데이터만 제공한다. 출구 대상의 본문·전체 그래프·모든 링크를 읽지 않는다.
기존 context 선택기의 공통 지침·문서/프로젝트 인덱스·프로젝트 필수/조건 문서·보안 원문·현재 채택 지식은 유지한다.
프로젝트는 기존 기본 프로필 또는 `--project docs/projects/<이름>/workflow.toml`로 선택한다.
전체 graph catalog는 도구 내부에서 경로를 검사할 때 읽는다. 모델에 전체 본문을 넣는다는 뜻이 아니다.
문서 위치 탐색은 [docs 인덱스](../../../docs/index.md), 작업의 다음 이동은 flow가 맡는다.

## 절차와 검증

실제 산출물·검사 보고서는 먼저 [evidence add](completion.md)로 task에 등록한다.
절차별로 그 결과를 증명하는 ID를 연결한다. 같은 근거를 여러 절차에 쓸 수 있으나 무엇을 증명하는지는 원문에서 대조한다.
아래는 현재 기본 라우트의 세 절차 ID다. 사용자 정의 라우트는 `flow context`의 순서를 따른다.

```sh
python3 tools/harness/run.py flow step my-flow scope --evidence PLAN
python3 tools/harness/run.py flow step my-flow execute --evidence RESULT
python3 tools/harness/run.py flow step my-flow inspect --evidence RESULT
python3 tools/harness/run.py flow validate my-flow --result passed --evidence RESULT --reason "요구·실제 결과·관련 오류와 남은 범위를 대조함"
```

순서 누락·중복 완료·증거 없는 절차를 거부한다. 검증은 한 진입에서 한 번 판정한다.
passed는 전체 절차 완료, 라우트의 필수 증거 유형, 필수 호출의 현재 통과 결과를 요구한다.
failed/blocked는 중간 절차에서 관측했어도 기록할 수 있다. 실패 검사 보고서는 artifact로 보존하며 성공 check로 등록하지 않는다.
실행/문법/링크 통과가 실제 요구 충족이나 내용의 진실성을 자동 증명하지는 않는다. reason에는 실제 관측과 한계를 기록한다.

## 호출·복귀·전이

```sh
python3 tools/harness/run.py flow move my-flow plan-research --reason "설계 선택에 필요한 원문 근거가 부족함"
python3 tools/harness/run.py flow context my-flow --read
# 호출받은 research:evidence의 실제 절차와 검증을 수행한다.
python3 tools/harness/run.py flow finish my-flow
```

`call`은 호출자의 완료 절차·입력·정확한 복귀 위치를 스택에 저장한다. 호출 중 `transition`으로 다른 노드를 지나도 원래 호출자로 돌아간다.
`finish`는 호출받은 경로의 검증 결과·근거를 전달하며 호출자의 다음 미완료 절차 또는 검증 판정에서 재개한다.
failed/blocked 결과도 그대로 반환한다. 부모의 성공 판정이나 필수 호출 통과로 바꾸지 않는다. 호출 중 실패 경로로 다른 노드에 넘어가 재계획만 성공해도 원래 요청한 검증의 성공으로 반환하지 않는다.
성공한 호출의 continuation에서 종료하면 원래 호출의 증거 유형도 충족해야 한다. 예를 들어 구현 호출이 문서 정리에서 끝날 때는 최종 artifact와 현재 check를 함께 검증에 연결한다. status의 return_contract에서 이 계약을 확인한다.
복귀하면 이전 부모 검증은 무효화하며 새 호출 결과를 반영해 다시 판정한다. 완료 절차 전체를 자동 재실행하지 않는다.
재귀 call과 과도한 스택 깊이는 거부한다.

```sh
python3 tools/harness/run.py flow move my-flow plan-backend --reason "현재 요구와 계획에서 Python 구현을 다음 작업으로 선택함"
```

`transition`은 현재 노드에서 등록된 다음 노드로 진행한다. 선조 호출의 복귀 맥락은 유지한다.
성공 경로에는 현재 소스에서 유효한 검증 통과가 필요하다. reason만으로 검증을 건너뛰지 않는다.
구현 라우트는 verify-work:check를 호출해 결과를 대조한다. 문서가 바뀌었거나 기준이 없으면 docs-maintenance:sync → 관련 문서 검증 → index로 진행한다. 등록된 조건부 종료에서 문서 내용이 같고 갱신이 불필요한 이유를 남기면 바로 종료할 수 있다.
현재 요청에 관련 사실·지식 변화가 있을 때 sync-wiki/sync-learning을 호출한다. 필요 없으면 그 판단을 근거에 남기고 인덱스 경로로 간다.
문서 편집 라우트는 검증 후 index로 이어지며, 위키 질문·탐색·읽기 감사는 수정 없이 종료할 수 있다.
루트에서 `finish`가 성공하면 `flow_status=finished`다. **task 완료는 별도의 기존 evidence review/verify/complete 계약을 따른다.**

## 이동 조건과 사용자 응답

| 조건/guard | 의미 |
|---|---|
| steps_complete | 현재 라우트의 모든 절차가 순서대로 완료됨. 그 자체는 검증 통과가 아님 |
| reason | 허용된 엣지에 관측·근거·이동 목적을 기록함. 권한·필수 검증을 대체하지 않음 |
| user_choice | 현재 질문 ID에 대응하는 실제 사용자 선택 기록과 원문 근거가 있음 |
| validated | 현재 소스·입력·증거에 유효한 검증 통과 |
| failed | 실패/막힘을 관측했거나 이전 통과 뒤 소스가 바뀌어 재검증이 필요함. 보완 경로에서만 사용 |

결과를 바꾸는 사용자 선택이 필요한 때에만 질문한다. 이미 승인된 작업의 단계별 재승인을 추가하지 않는다.

```sh
python3 tools/harness/run.py flow ask my-flow --question "다음에 구현할 흐름은 어느 쪽인가요?"
# 실제 질문을 사용자에게 전달하고 답변 원문을 task 증거 USER_REPLY로 연결한다.
python3 tools/harness/run.py flow answer my-flow --question-id 실제질문ID --choice backend --evidence USER_REPLY --reason "현재 질문에 사용자가 백엔드 흐름을 선택한 원문을 확인함"
python3 tools/harness/run.py flow move my-flow choose-backend
```

ask는 현재 노드에 등록된 user_choice 엣지의 선택지를 고른다. 응답 전에는 같은 흐름의 이동·절차·완료를 막는다.
별개의 독립 작업은 다른 task/flow로 진행할 수 있다. 시간 경과·무응답을 답변으로 만들지 않는다.
잘못된 질문 ID·다른 선택·증거 누락을 거부하고 소비한 답변은 다음 이동에 재사용하지 않는다.
도구는 사용자의 신원을 인증하지 않는다. 에이전트는 실제 답변이 없으면 answer를 기록하지 않는다.

## 변경·재진입·중단

검증 뒤 소스 내용/실행 권한이나 증거가 바뀌면 성공 경로를 거부한다. status의 stale을 확인한다.
실패 또는 통과 뒤 소스 변경에는 현재 노드의 `retry-<스킬>-<라우트>` 엣지로 재진입하여 필요한 절차·검증을 다시 수행한다.
등록된 실패 경로가 다른 설계/계획으로 돌아갈 수도 있다. 실패 판정은 성공 경로로 전이하는 근거가 아니다.

```sh
python3 tools/harness/run.py flow move my-flow retry-plan-project-plan --reason "새 결과로 계획의 전제가 바뀌어 현재 근거에서 다시 검토함"
python3 tools/harness/run.py flow block my-flow --reason "필수 로컬 검증 환경을 사용할 수 없어 다음 진행 조건이 충족되지 않음"
python3 tools/harness/run.py flow restart my-flow --reason "변경된 요구/입력 또는 해결된 차단 조건의 새 근거에서 재시작함"
```

restart는 바뀐 계약/catalog·오래된 근거 또는 중단 뒤 **새 소스/계약/증거 내용**이 있을 때 명시적으로 수행한다.
스택·기존 완료 절차를 버리고 entry(또는 --node)에서 새로 시작하며 이전 이동 기록은 보존한다. 횟수 제한을 초기화하지 않는다.
소스/근거 변경이 없는 통과 결과를 반복해서 얻으려고 재시작하지 않는다. 스킬/절차 계약 변경은 명시적 재시작이 필요하다. catalog 해시는 라우트/경로 TOML뿐 아니라 소유 SKILL·참조 절차의 실제 내용도 포함한다. 추가 입력은 최초 evidence entry 서명에 묶어 유효한 다른 파일로 바꿔치기해도 거부한다.

기본 한도는 이동100회·호출 깊이8·같은 노드에서 진전 없는 방문3회다. start의 --max-moves/--max-depth/--max-visits로 작업에 맞게 정한다.
새 증거 ID·설명·실행 시각만 바꾸는 것은 진전이 아니다. 소스/요구 또는 증거 내용이 달라야 한다. 총 이동 한도는 새 근거가 생겨도 유지한다.
한도 도달은 blocked로 저장한다. 실제 해결 없는 무한 재시도를 하지 말고 원인·남은 작업을 기록한다.
상태/기록은1 MiB·이벤트1000개로 제한한다. 계속해야 하는 별도 범위는 기존 기록을 보존하고 별도 task/flow로 잡는다.

동시 쓰기는 실행별 비차단 잠금과 원자적 교체를 사용한다. 상태 무결성 checksum과 순서/형식 검사를 수행한다.
오래된 명령에는 --expect-revision을 사용한다. 잠금이 바쁘면 현재 작성자가 끝나길 확인하며 활성 잠금을 삭제하지 않는다.
checksum은 우발적 손상을 탐지하며 로컬 파일 편집 권한을 가진 작성자의 신원·기록 진실성을 인증하지 않는다.
다른 노트북에는 로컬 flow 파일이 없을 수 있다. 공유 task/계약/근거에서 현재 조건을 확인해 새 로컬 흐름을 시작한다.

## 검증 범위

새 스킬을 기존 skill create/from-knowledge로 만들면 그래프가 있는 레포에서는 SKILL 본문을 수행하고 artifact로 확인하는 기본 main 라우트를 함께 만든다. 상세 분기·코드 검사·호출/전이는 실제 요청에 맞게 보완한다. 기존 스킬의 계약을 자동 덮어쓰지 않는다.

등록 계약·이동·재진입·대기·입력/증거·소스 변경·한도·잠금·CLI·선택 읽기는 [회귀 검사](../tests/test_skill_flows.py)에서 확인한다.
고정된 fixture와 실제 로컬 검사 결과는 제어 계약의 근거다. 임의의 프로젝트에 대한 자동 품질 승인이나 모델 행동의 완전한 보장을 뜻하지 않는다.

entry_checks/result_checks는 design/alignment로 제한된 검사를 선언한다. 입력 역할과 준비/산출물 검사를 구분하고 임의 표현식이나 명령을 실행하지 않는다. 생성한 구현/debug 스킬은 기본 main 라우트에도 현재 design/alignment 입력을 요구한다.

flow의 소스 상태도 [검사 재사용 경계](verification.md#작업-기록과-코드-검사의-재사용)를 사용한다. 명시적으로 독립인 검사만 무관한 task 기록을 제외하며 현재 작업의 원문/입력·증거·선행 작업과 실행/설정은 계속 보호한다.

## 의도 변경과 발견 기록

새 flow 상태는 version=2다. request/contract와 재진입 진행 지문에서 발견 ID를 제외한 `evidence.intent_contract`를 사용한다. 동일한 목표·범위·제약·입력·선행 작업·수용 기준/방법 안에서 findings를 추가해도 완료한 step·호출 결과·현재 위치를 유지하며 restart가 필요 없다. 설계/결정 근거와 소스의 변경 검출은 유지한다. 발견 추가만으로 같은 노드를 무한 재시작할 수도 없다.

완료 리뷰는 발견 목록을 포함하는 기존 계약을 사용하므로 새 결함을 처리하고 회귀와 리뷰를 갱신해야 한다. flow의 위치/정렬 유지와 task의 완료 허용은 별개다.
이전 version=1 상태는 당시 전체 계약 의미를 유지한다. inspect/context는 원본을 쓰지 않으며, 이유와 현재 입력을 지정한 명시적인 restart에서만 이력은 보존하고 version=2로 전환한다. 이전 v1 alignment가 의도 변경/발견 추가로 오래됐으면 새 v2 정렬 근거를 먼저 연결한다. 원본 상태/정렬/완료 기록을 자동으로 다시 쓰지 않는다.

## 문서 변경에 따른 조건부 종료

Python/Svelte 구현·Postgres change·Docker configure·verify-work repair는 `finish=false`와 기존 문서 continuation을 유지하면서 `finish_when="documents_unchanged"`를 선언한다. 필수 호출·검증·증거와 수용 조건을 충족한 뒤에만 조건부 finish를 사용할 수 있다.

조건부 종료를 사용할 구현 flow는 실제 수정 전에 시작한다. 해당 frame 진입 때 정본 문서의 경로와 SHA-256을 저장한다. Git 변경 목록·커밋·mtime 대신 파일 내용 해시를 비교하므로 Git 없는 폴더에서도 동작한다. 이미 수정한 뒤 만든 기준을 수정 전 상태라고 주장하지 않는다.

- `docs/`와 `tools/harness/docs/`의 정본·설정/문서 자료, 그 밖 Markdown/MDX/RST/AsciiDoc 및 Markdown 양식을 비교한다. `docs/tasks/`의 수행 기록과 runtime 로그는 문서 동기화 대상에서 제외한다.
- 동일 내용 재저장/시간 변경은 무변경이다. 내용 수정·추가·삭제·이름 변경은 변경이다. `flow status/context`의 `documentation.changed_paths`에서 경로를 확인한다. 형제 원문 전체를 모델에 읽히지 않는다.
- 변경이 없으면 `flow finish <실행ID> --reason "현재 정본이 그대로 유효해 문서 갱신이 불필요한 구체적 이유"`로 문서 단계를 생략한다. 이유가 없거나 검증/필수 호출이 없으면 거부한다. 이벤트에는 무변경 판정과 이유가 남는다. task 완료는 여전히 별도 완료 계약을 따른다.
- 변경이 있거나 기준이 없으면 기존 문서 경로로 이어간다. 문서 수정 필요 여부의 의미는 에이전트가 검토한다. 파일이 안 바뀌었다는 사실만으로 요구/사용법이 올바르다고 자동 승인하지 않는다.
- retry와 명시 restart는 원래 문서 기준을 보존해, 이미 바뀐 문서를 새 기준으로 덮어 숨기지 않는다. 기준 없는 이전 frame은 새 기준을 추측하지 않고 기존 문서 경로를 사용한다. 호출/복귀 때 호출자의 기준도 보존한다.

이 조건은 문서 단계의 불필요한 반복만 줄인다. 코드·설계/근거·권한·환경의 변경 검출과 필수 검사·정상/실패·회귀·완료 리뷰는 유지한다. 등록되지 않은 route의 종료 조건은 바뀌지 않는다.
