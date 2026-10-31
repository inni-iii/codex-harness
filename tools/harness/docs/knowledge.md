# 학습·기억·프로젝트 간 공유

단일 원본은 docs/knowledge/catalog.json이다. 개인 홈·외부 DB·MCP·별도 모델은 필요 없다.
진행 상태는 task notes/인수인계에, 재사용할 교훈은 catalog에 둔다.
project는 workflow.toml 디렉터리의 slug이며 null은 이 하네스의 공통 범위다. 개인 전역 설정을 뜻하지 않는다.
노트북 경로·remote URL 해시를 ID로 쓰지 않아 같은 프로젝트를 worktree/다른 노트북에서 이어갈 수 있다.

## 기록·검토

레포 안의 JSON 명세에서 id/title/lesson/conditions는 필수다. project는 null 또는 slug이며 exclusions/topics/paths/kinds/sources는 문자열 목록이다.
sources에는 HTTPS 원문 또는 레포 상대경로를 적는다. 전체 대화·원본 도구 출력·비밀값은 넣지 않는다.

```json
{"id":"retry-boundary","title":"외부 재시도","lesson":"SDK와 helper의 중첩 재시도를 확인한다.","conditions":"외부 API 재시도 변경","project":null,"topics":["external-api"],"sources":["docs/tasks/example/notes.md"]}
```

```sh
python3 tools/harness/run.py knowledge add docs/tasks/example/lesson.json
python3 tools/harness/run.py knowledge list
python3 tools/harness/run.py knowledge search "재시도"
python3 tools/harness/run.py knowledge show retry-boundary
python3 tools/harness/run.py knowledge review retry-boundary --state evaluated --reason "재현 확인" --evidence docs/tasks/example/result.md
python3 tools/harness/run.py knowledge review retry-boundary --state adopted --reason "적용 조건 검토" --evidence docs/tasks/example/result.md
```

예시 경로는 실제 작업으로 바꾼다. review는 파일의 존재·해시를 연결하며 내용의 진위/테스트 성공을 자동 판정하지 않는다.
candidate는 자동 읽기에 포함하지 않는다. context는 프로젝트/공통 범위·kind/topic/path의 OR 선택 조건·현재 증거가 맞는 adopted만 선택한다.
conditions/exclusions는 사람이 읽는 적용/제외 조건이다. 선택기가 자연어의 충족 여부까지 판정하지 않으므로 에이전트가 원문에서 적용 여부를 판단한다.
증거 변경/누락은 기존 채택을 자동 재승인하지 않는다. show에서 확인해 재검토한다.

```sh
python3 tools/harness/run.py knowledge promote project-rule common-rule --reason "공통 적용 조건 검토"
python3 tools/harness/run.py knowledge review old-rule --state superseded --replacement new-rule --reason "새 계약으로 대체"
```

promote는 adopted 프로젝트 지식에서 별도 공통 candidate를 만든다. 원본을 보존하고 공통성을 다시 검토한다.
superseded에는 같은 범위의 다른 adopted가 필요하며 과거 기록을 지우지 않는다.

## 공유

```sh
python3 tools/harness/run.py knowledge export docs/tasks/example/bundle.json --project example
python3 tools/harness/run.py knowledge import docs/tasks/example/bundle.json --dry-run
python3 tools/harness/run.py knowledge import docs/tasks/example/bundle.json
```

export는 adopted만 내보낸다. --project가 없으면 모든 범위, 지정하면 해당 프로젝트와 공통 범위를 포함한다. 공유 전 범위를 확인한다.
checksum은 전송 오류 확인용이며 발행자 인증이 아니다. import는 로컬 파일만 읽고 candidate로 낮춘다.
동일 ID·내용은 건너뛰고 다른 내용은 충돌로 표시해 전체 적용을 중단한다. 파일 내용으로 명령을 실행하지 않는다.
list/search/show와 import --dry-run은 저장소나 디렉터리를 생성하지 않는다. 쓰기는 배타 잠금과 단일 catalog 원자 교체를 사용한다.
catalog와 bundle의 한도는 각각 2 MiB다. 저장·내보내기는 들여쓰기/개행을 포함한 실제 JSON 크기를 검사한다. 한도를 넘으면 기존 catalog를 보존하고, 내보내기 범위나 기록 크기를 조정하도록 오류를 반환한다.
비정상 종료로 .runtime/knowledge.lock이 남으면 활성 writer를 확인한 후 로컬 잠금만 정리한다.

## Codex 훅

이벤트·현재 작업 연결·저장 범위·실제 실행의 신뢰 조건은 [생명주기 훅](hooks.md)을 따른다. UserPromptSubmit 라우팅 훅 등록은 제거했으며 [자동 연결은 보류](execution.md#일반-codex-대화창의-자동-호출)했다.
SessionStart는 기본 workflow의 프로젝트/공통 범위에서 kind=plan 또는 learning/resume에 맞는 현재 채택 지식 최대10개를 안내한다. lesson·적용·제외 조건은 함께 전달하고, 전체8,000자 한도에 맞지 않으면 원문 조회 명령을 전달한다. Codex 자체의 출력 제한은 별도로 적용된다.
PreCompact는 기존 최대100개 task의 메타데이터 경로를 유지하고, Interrupt/Stop은 명시적으로 연결한 task만 기록한다. 대화 요약·교훈 추출·도구 입출력 수집·추가 모델 호출은 하지 않는다. 의미 있는 결정/실패는 작업자가 notes와 knowledge에 남긴다.
