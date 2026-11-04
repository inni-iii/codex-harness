# 프로젝트 문서 저장과 연결

새 프로젝트는 `docs/<프로젝트>/`에 생성한다. 같은 기능의 요구·계약·설계·현재 검증 요약은 `features/<기능>/`의 정본을 갱신한다. 문서 작성이 필요한지, 어느 기능/공통 섹션에 속하는지, 어떤 작업에서 읽어야 하는지는 현재 에이전트가 판단한다.

## 배치

| 소유 내용 | 위치 |
|---|---|
| 작은 프로젝트 지도·개요·보안·읽기/검사 설정 | `docs/<프로젝트>/{index.md,brief.md,security.md,workflow.toml}` |
| 같은 기능의 정본 | `features/<기능>/{spec.md,design.md,verification.md}` 중 필요한 파일 |
| 공통 설계·결정·운영 | `architecture/`, `decisions/`, `operations/` 중 필요한 폴더 |
| 작업의 진행·실패·검사 이력 | `docs/tasks/<작업>/` |
| 원본 로그·검사 보고서 | `.runtime/` |

빈 폴더나 문서 세트를 미리 만들지 않는다. 작은 내부 수정은 문서 변경이 필요 없을 수 있다. 기존 정본에 반영할 수 있는 내용을 날짜/단계별 Markdown 보고서로 프로젝트 루트에 계속 쌓지 않는다. `tasks`, `knowledge`, `projects`는 프로젝트 이름으로 사용할 수 없다.

## 기능 문서 저장

다음은 실제 프로젝트가 정해졌을 때 이름·내용·조건을 바꾸어 레포 루트에서 실행하는 예다. 먼저 `project demo --goal "실제 목표"`로 프로젝트를 생성하고, 에이전트가 현재 요구에 맞는 Markdown 본문을 `.runtime/login-spec.md`에 작성한다.

```sh
python3 tools/harness/run.py document upsert \
  --project docs/demo/workflow.toml \
  --feature login --kind spec \
  --source .runtime/login-spec.md \
  --role "로그인의 입력·허용/거부·실패 복구 계약" \
  --path 'backend/auth/**' --topic login
python3 tools/harness/run.py context --kind implement \
  --project docs/demo/workflow.toml --paths backend/auth/session.py --read
python3 tools/harness/run.py doctor
```

`--source`는 존재하는 레포 내부 UTF-8 Markdown 본문 파일이다. 2MiB 이하의 비어 있지 않은 본문을 사용한다. 프로젝트/기능 이름은 소문자 영문·숫자·하이픈 slug다. `--kind`는 `spec`(기본값), `design`, `verification`이다. `--role`은 실제 역할을 설명하는 한 줄이다.

이 명령은 다음을 함께 갱신한다.

1. `docs/demo/features/login/spec.md`: 기존 파일이 있으면 같은 경로를 갱신한다.
2. 기능 지도와 `features/index.md`·프로젝트 지도·`docs/index.md`: 기존 설명을 보존하고 필요한 설명 있는 상대 링크를 연결한다.
3. 선택한 `workflow.toml`: 문서의 `context.rules`에 경로/주제와 읽을 이유를 연결한다. 링크된 모든 본문을 필수 읽기로 넣지 않는다.

새 문서는 `--path` 또는 `--topic`이 필요하며 둘 다 반복할 수 있다. 조건은 OR이다. `--path`는 레포 기준 glob이고 `--topic`은 이후 context에서 지정하는 주제다. 재저장 때 조건을 생략하면 기존 조건을 유지한다. 도구가 관리하는 조건은 명시한 새 조건으로 갱신한다. 수동 규칙의 조건과 충돌하면 덮어쓰지 않고 실패하므로 해당 규칙을 직접 검토한다. 전역/종류 조건에 묶인 기능 문서는 선택 범위를 먼저 수정해야 한다.

같은 입력을 반복해도 문서/규칙/지도 항목을 추가로 늘리지 않는다. 심볼릭 링크·경로 탈출·예약 이름·잘못된 조건은 거부한다. 동시 저장은 로컬 잠금으로 충돌을 보고하고, 일부 파일 저장 실패 시 자신이 쓴 내용만 되돌린다. 다른 편집자의 변경은 보존한다. 프로세스 강제 종료·시스템 장애에 대한 데이터베이스식 원자성은 제공하지 않는다. 실패를 자동 재실행하지 말고 현재 파일과 잠금 소유를 확인한다.

`architecture/` 등 공통 문서, 파일 이동, 수동 규칙 변경은 에이전트가 같은 작업에서 지도/조건/참조를 갱신한다. 이 명령은 기능 정본 저장을 지원하며 모든 문서 편집을 감시하는 백그라운드 훅은 아니다. 사용자는 기능 구현/검증을 요청하면 되고 에이전트가 문서 필요 여부와 연결 절차까지 수행한다. 하네스 지침을 적용하지 않는 외부 편집까지 자동 보장하지 않는다.

## 검사와 읽기

새 생성 프로필은 `[documentation] layout = "feature-folders"`를 선언한다. `doctor`는 직접/legacy 경로의 프로필을 모두 찾고 새 배치에서는 다음을 검사한다.

- 프로젝트 루트의 허용 개요/보안/지도 외 Markdown, 알 수 없는 섹션 폴더와 기능 폴더 밖 문서
- 기능 본문의 경로/주제 읽기 조건 누락 또는 전역/종류 조건으로 과도하게 읽는 등록
- 기존 폴더 지도 계약에 따른 지도·직계 파일/하위 지도 링크·역할 설명 누락

설명/본문의 의미나 선택 조건의 적절성은 에이전트 검토 대상이다. `context`는 선택된 본문과 그 조상 지도를 읽고 형제 기능의 본문을 펼치지 않는다. 선택한 workflow를 `--project`로 지정하거나 [기본 프로필](project-workflows.md)에 연결해야 프로젝트 규칙이 적용된다.

## 이전 경로

배치 선언이 없는 기존 `docs/projects/<프로젝트>/workflow.toml`은 계속 읽고 검사할 수 있다. 새 생성은 직접 경로만 사용하고 같은 이름의 이전 폴더가 있으면 중복 정본 생성을 거부한다. 기존 프로필에 새 배치 선언만 붙여 자동 이동했다고 하지 않는다.

```sh
python3 tools/harness/run.py document migration-plan \
  --project docs/projects/old/workflow.toml
```

이 명령은 읽기 전용 경로 대응표와 루트 문서의 기능/공통 분류 필요 여부만 반환한다. 실제 이동·본문 분류·현재 링크/프로필/인덱스 갱신은 대상 레포에서 수행하고 doctor/context와 관련 검사를 확인한다. 과거 세션·원본 로그·검증 보고서를 경로 문자열 치환으로 고쳐 쓰지 않는다. 완료 근거는 원본 바이트/해시를 보존하고 필요한 위치 변경만 출처와 함께 기록한다.
