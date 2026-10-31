# 프로젝트별 워크플로

공통 하네스와 프로젝트 규칙을 분리한다. PostgreSQL 사용은 확정했고 현재 활성 프로젝트는 없다. 실제 앱·브랜드·DB 버전/ORM/확장은 프로젝트에서 정한다.

## 만드는 방법

주제가 들어오면 다음을 실행한다.

```sh
python3 tools/harness/run.py project demo --goal "프로젝트의 실제 목표"
python3 tools/harness/run.py context --kind plan --project docs/projects/demo/workflow.toml --read
```

project는 docs/projects/demo/index.md·brief.md·security.md와 draft workflow.toml을 만든다. 기존 폴더를 덮어쓰지 않는다.
security.md는 보호 자원·권한·비신뢰 경계·검증 조건을 채울 초안이며 생성만으로 보안 설계가 완료되지는 않는다.
상세 작성 절차와 로컬 검사는 [보안 관리](security.md)를 따른다.
코드 scaffold·설치·모델 호출·프로필 활성화는 하지 않는다.
brief에 요구와 제약을 채우고 실제 코드와 명령이 준비되면 검사를 등록한다.

목표에서 작업을 도출하고 전후 갭을 다시 재는 판단은 [프로젝트 진행](../../../.agents/skills/plan-project/references/project-lifecycle.md)을 따른다. 생성된 개요·인덱스는 그 연결을 작성할 안내이며, 요구 도출·갭 판정·작업 배정을 자동 실행하지 않는다. 별도 계획이 필요하면 실제 문서를 만든 뒤 인덱스와 관련 context 규칙에 연결한다.

## 자료와 명령 연결

다음은 설정 형식을 설명하는 예시다. frontend/backend와 각 스크립트가 실제로 있는 프로젝트에서 조정해 사용한다.
기본 템플릿의 checks=[]·impacts=[]는 아래 배열 테이블을 추가할 때 제거한다.

```toml
version = 1
name = "demo"
state = "draft"

[security]
state = "draft"
document = "docs/projects/demo/security.md"
document_sha256 = ""
assets = []
trust_boundaries = []
controls = []

[context]
documents = ["docs/projects/demo/brief.md"]

[[context.rules]]
paths = ["backend/**"]
documents = ["docs/projects/demo/domain-rules.md"]

# Both documents below must exist before adding these rules.
[[context.rules]]
topics = ["resume", "handoff"]
documents = ["docs/projects/demo/checkpoint.md"]
when = "Restore decisions, failed approaches and verification state."

[[context.rules]]
kinds = ["debug"]
documents = ["docs/projects/demo/lessons.md"]

[[checks]]
id = "app-backend"
command = ["uv", "run", "pytest", "tests", "--junitxml={report}"]
cwd = "backend"
paths = ["backend/**", "shared/**"]
test_summary = "junit"
cacheable = false
timeout = 120

[[checks]]
id = "app-frontend"
command = ["npm", "run", "check"]
cwd = "frontend"
paths = ["frontend/**", "shared/**"]
cacheable = false
timeout = 120

[[checks]]
id = "app-smoke"
command = ["npm", "run", "test:smoke", "--", "--reporter=junit", "--outputFile={report}"]
cwd = "frontend"
paths = ["frontend/tests/smoke/**"]
test_summary = "junit"
always = true
cacheable = false
timeout = 120

[[checks]]
id = "app-build"
command = ["npm", "run", "build"]
cwd = "frontend"
paths = ["frontend/**", "shared/**"]
tier = "full"
cacheable = false
timeout = 180

[[impacts]]
paths = ["backend/schema/**", "shared/**"]
checks = ["app-backend", "app-frontend", "app-smoke"]
reason = "API contract changed; verify producer and consumers."
```

test:smoke는 실제 JUnit 출력 지원 테스트 runner를 호출하는 프로젝트 스크립트여야 한다.
예시에서는 [Vitest JUnit reporter](https://vitest.dev/guide/reporters.html)를 가정한다. 다른 runner의 옵션을 섞지 않는다.
백엔드 테스트·프론트 정적 검사만으로 전체 사용자 연결을 검사했다고 하지 않는다.
app smoke 자체가 어떤 실제 경계를 확인하는지 정의한다.

## 선택 규칙

- context는 `docs/index.md`와 선택한 프로필 옆의 `index.md`가 있으면 필수 본문보다 먼저 한 번 포함한다. 링크를 재귀로 읽지 않는다. 인덱스가 없는 기존 프로필도 종전 규칙대로 읽으며 명시된 필수·보안 문서를 생략하지 않는다.
- 인덱스에서 실제 질문에 맞는 정본/절을 고른 뒤 직접 읽거나 조건 규칙으로 선택한다. `--paths`는 임의 문서 직접 읽기가 아니다. 자세한 방법은 [선택 읽기](../../../.agents/skills/docs-maintenance/references/navigation.md)를 따른다.
- --project는 파일 경로다. 모든 cwd·paths·문서 경로는 workflow 파일 위치가 아닌 레포 루트 기준이다.
- 기본 하네스 checks와 프로젝트 checks를 합친다. ID는 합쳐진 목록에서 유일해야 한다.
- paths는 fnmatch 규칙이다. *는 /도 포함한다. 쉘 glob·gitignore 규칙과 혼동하지 않는다.
- 패턴은 실제 소스 이름과 일치하는 레포 상대 표기다. ./·빈 경로 조각·../·역슬래시·끝 슬래시는 지원하지 않는다. 디렉터리 전체는 backend/auth/**처럼 쓴다.
- checks의 지원 필드는 id, command, cwd, paths, cacheable, always, covers_behavior, timeout,
  max_output_bytes, allow_flaky, tier, run_at, test_summary다. 알 수 없는 필드는 오류로 거부한다.
  time_out 같은 오타나 run_after/parallel 같은 미지원 순서·병렬 설정이 조용히 무시되지 않게 한다.
  task.depends_on은 작업 관계 기록이며 검사 DAG나 자동 에이전트 실행 기능이 아니다.
- 기본 tier=change는 경로가 맞으면 선택한다. tier=full은 --full 또는 impacts가 명시적으로 선택할 때 실행한다.
- always=true는 문서 예외가 아닌 변경이 있을 때 선택한다. 별도 설정이 없으면 하네스/도구 변경에도 실행되므로 가볍게 유지한다.
- impacts는 지정된 경로가 바뀌면 다른 검사도 추가한다. 선택 이유는 --plan과 실행 report에 남는다.
- 항상 실행하는 smoke만으로 미등록 경로가 가려지지 않는다. 해당 파일을 덮는 실제 checks.paths가 필요하다.
- 선택한 workflow 파일을 바꾸면 일반 등록 검사를 다시 선택한다. 문서 변경만으로 앱 suite를 강제하지 않는다.
- draft 프로필은 context에서 읽을 수 있지만 check는 needs_configuration을 반환한다.
- active는 실행 가능한 실제 검사가 준비됐다는 뜻이다. 보안 검토의 미결 여부는 별도 상태로 관리하며 전체 프로젝트의 검증 충분성과 구분한다.

## 보안 설계와 활성화 조건

실제 검사 명령이 준비되면 프로젝트를 active로 사용하면서 보안 설계를 병렬로 보완할 수 있다.
보안 문서 미작성·초안·검토 해시 불일치는 프로젝트를 읽거나 로컬 테스트를 실행하는 전역 잠금이 아니다.
이 경우 security_review에 미결 사유를 남기며 해당 범위의 보안 완료·전체 완료 근거로는 사용할 수 없다.
잘못된 명령/설정 형식·레포 밖 경로는 계속 오류다. 실행 명령 자체가 없는 프로젝트 draft는 기존처럼 needs_configuration이다.
security.state=reviewed는 기록한 문서와 자원·경계를 검토했다는 뜻이며 개별 항목에는 pending이 남을 수 있다.

1. security.md에 실제 자원·주체·신뢰 경계·보호 조건·실패 정책을 채운다. `상태: draft`와 `작성 필요`를 남긴 양식은 검토 미결로 표시한다.
2. `[security]`의 assets·trust_boundaries에 실제 대상을 적는다. 빈 배열이나 TODO 같은 단독 자리표시자는 허용하지 않는다.
3. 아래 8개 area를 각각 한 번 평가한다. required이면 보호 조건·적용 경로·실제 테스트 ID를, not_applicable이면 제외 이유를, 진행 중이면 pending과 영향 경로를 적는다.
4. 필수 테스트는 프로젝트 [[checks]]에 등록하고 test_summary=unittest 또는 junit을 연결한다. doctor·패턴 검사·실행 수 없는 정적 검사만으로 대신할 수 없다.
5. 실제 검토한 문서의 정확한 SHA-256을 document_sha256에 기록하고 security.state=reviewed로 바꾼다. 프로젝트 active 전환과 보안 완료는 별도 판단이다.

| area | 검토 대상 |
|---|---|
| authorization | 인증·세션·소유자·역할·조직 권한 |
| inputs-files | 입력·출력·파일·경로·업로드 |
| external-tools | 외부 API·URL·MCP·모델 응답과 실행 |
| dependencies | manifest/lock·출처·설치·취약점 조회 |
| secrets-logging | 비밀값·개인정보·로그·trace |
| browser | HTML·쿠키·CORS/CSRF/CSP·SSR |
| execution | 프로세스·파일·네트워크 실행 권한 |
| abuse | 크기·시간·동시성·중복·재시도·비용 |

다음은 한 area의 등록 예다. 나머지도 실제 프로젝트에 맞게 평가한다. controls=[]를 제거한 뒤 배열 테이블을 추가한다.

```toml
[[security.controls]]
area = "authorization"
status = "required"
description = "비소유자는 문서 ID를 알아도 읽거나 수정할 수 없다."
paths = ["backend/**", "frontend/**"]
checks = ["app-backend"]

[[security.controls]]
area = "external-tools"
status = "not_applicable"
description = "현재 기능은 로컬 데이터만 처리하며 외부 요청·모델·도구 호출이 없다."
```

not_applicable에는 paths/checks를 넣지 않는다. 공개 정적 사이트 등 권한 모델이 없는 경우도 근거를 적어 구분한다.
설계 판단 자체는 검토자가 책임진다. 해시·필드가 존재해도 내용을 허위로 작성하거나 테스트가 무관하면 안전성을 증명하지 못한다.

문서 해시는 레포 루트에서 다음처럼 계산한다. 도구가 검토 상태를 자동 승인하지는 않는다.

```sh
python3 -c "import hashlib,pathlib; print(hashlib.sha256(pathlib.Path('docs/projects/demo/security.md').read_bytes()).hexdigest())"
```

검토 문서가 바뀌면 해시 불일치를 미결로 기록한다. 일반 구현과 로컬 검사는 계속하고, 검토 후 해시와 controls를 갱신한다.
해당 paths의 변경은 feature/integration/final에서 연결한 테스트를 tier/run_at보다 우선해 선택한다. edit에서 미루면 deferred_checks로 남는다.
프로필 변경과 --full도 필수 보안 테스트를 선택한다. 보안 문서의 문구 수정만으로 모든 제품 보안 테스트를 재실행하지 않는다.
실행 수 0·전체 skip/expected failure·누락 보고서·실패·실행 오류가 있으면 필수 테스트를 통과로 보고하지 않는다.
기존 active 프로필에 [security]가 없어도 로컬 검사는 가능하지만, 보안 검토를 완료한 것으로 면제하지 않는다.

## 동시 작업의 미결 범위와 완료 판정

예를 들어 세션 A가 인증 정책을 검토하고 세션 B가 독립적인 표시 화면을 구현한다면:

```toml
[[security.controls]]
area = "authorization"
status = "pending"
description = "인증 역할과 세션 폐기 조건을 별도 작업에서 보완 중이다."
paths = ["backend/auth/**", "frontend/session/**", "shared/identity/**"]
checks = ["auth-tests"]
```

다른 area의 판단과 검토 문서 해시가 유효하면 이 미결은 지정한 경로와 연결한 검사에 한정한다.
checks는 아직 준비되지 않았으면 생략할 수 있다. 영향 경로를 모르면 생략하며 이때 전체 범위 미결로 취급한다.
공유 schema·API의 소비자도 paths에 포함하고 impacts로 연결한다. 명시적인 impacts가 해당 checks를 선택하면 그 미결도 전파한다.
경로 도구가 의미상 독립성을 증명하지는 않는다. 단지 빠르게 진행하려고 실제 영향 경로를 줄이지 않는다.

| 검사 상황 | 검사 실행과 상태 | CLI 종료 코드 |
|---|---|---|
| edit/feature에서 관련 보안 미결·등록 검사 통과 | 실행 후 checks_passed_security_pending, completion_ready=false | 0: 개발 단계 실행 성공 |
| integration/final 또는 --full에서 관련 보안 미결 | 테스트는 실행하되 완료 판정 보류 | 2 |
| 해당 범위의 보안 미결·실패·deferred 없음 | passed. 별도의 기준별 완료 리뷰는 필요 | 0 |
| 무관한 범위에만 미결 | 해당 검사 통과 가능. project_pending에 남은 항목 표시 | 0 |
| 실제 테스트 실패·실행 오류 | 실패 유지. 검토 대기가 실패를 덮지 않음 | 2 |

applicable_pending은 이번 범위의 미결, project_pending은 프로젝트 전체의 미결이다.
--full은 변경 경로와 무관하게 전체 미결을 포함한다. 문서 미작성·전체 설계 draft·해시 불일치는 아직 범위를 한정할 근거가 없으므로 전체 미결이다.
checks_passed_security_pending은 task 완료 증거로 첨부할 수 없다. CLI 0만 보고 제품/보안 완료로 바꾸지 않는다.
여러 세션의 파일 격리·검사 사본·통합은 [협업 절차](../../../.agents/skills/plan-project/references/collaboration.md)와 [검증 명세](verification.md)를 따른다.

--paths는 실제 변경을 자동 대체하는 옵션이다. 전체 영향 검사를 줄이기 위해 관련 파일을 의도적으로 빼지 않는다.
자동 경로 탐지는 staged·unstaged·untracked를 포함한다.
미등록 앱 경로는 실행 전에 차단한다. 모든 앱 코드를 documentation 예외에 넣지 않는다.

## 활성화와 확인

```sh
python3 tools/harness/run.py doctor
python3 tools/harness/run.py check --project docs/projects/demo/workflow.toml --plan
python3 tools/harness/run.py check --project docs/projects/demo/workflow.toml
```

기본 프로젝트로 쓰려면 tools/harness/harness.toml에 다음을 넣는다.

```toml
[project]
workflow = "docs/projects/demo/workflow.toml"
```

--project가 있으면 기본 선택보다 우선한다. staging 검사에서도 내보낸 index의 프로필과 소스를 사용한다.
의존성 설치는 check가 자동 수행하지 않는다. 필요한 설치·fixture·로컬 앱 시작·정리 절차는 프로젝트에서 명시한다.
외부 상태가 변하는 검사에는 캐시를 켜지 않는다. 네트워크·실서비스·SSH 쓰기를 암묵적으로 추가하지 않는다.

## 규칙을 찾아 읽는 방법

```sh
python3 tools/harness/run.py context --kind implement --paths backend/items/service.py --topic api --project docs/projects/demo/workflow.toml
python3 tools/harness/run.py context --kind debug --paths frontend/src/Search.svelte --topic async --read
```

context는 .agents/context.toml의 kind·topic·paths 조건과 프로필 문서 규칙으로 읽을 파일과 이유를 반환한다.
프로젝트 context.rules도 kinds·topics·paths 중 하나 이상으로 선택한다. 여러 조건은 OR이며, 모두 만족해야 하는 조건이 아니다.
예를 들어 kinds=["debug"]와 paths=["backend/**"]를 같은 규칙에 적으면 모든 디버깅 또는 backend 변경에서 읽는다.
여러 조건을 모두 만족해야 하는 더 좁은 규칙이 필요한 경우 현재 도구가 AND 조건을 지원한다고 가정하지 않는다.
규칙의 documents는 기존 Markdown 파일이어야 하며, when은 선택 이유를 설명할 수 있다.
프로젝트 규칙의 topics와 context.topics에 선언한 이름은 선택한 프로젝트 안에서만 사용할 수 있다.
context.topics는 주제 등록이며 자동 활성화가 아니다. --topic으로 지정하거나 경로/작업 종류 조건이 맞아야 해당 문서가 선택된다.
예시의 checkpoint/lessons는 필요한 시점에 실제로 작성하고 규칙을 추가한다. 템플릿의 주석은 자동 설정이 아니다.
공유 주제(async 등)의 참조는 requires_skill=true로 해당 언어 스킬이 선택됐을 때만 추가할 수 있다.
--read는 실제 파일 내용도 반환한다. 파일을 나열한 것만으로 에이전트가 읽었다고 보장하지 않는다.
AGENTS.md는 작업 전에 이 결과의 원문을 읽고, 새 경계를 발견하면 추가 탐색하도록 지시한다.
Codex의 기본 스킬 탐색도 유지한다. 이 도구는 실행 중 모델 컨텍스트를 강제로 주입하는 hook이 아니다.
프로젝트의 비표준 코드 위치·문서가 늘어나면 context 규칙과 검사 경로도 함께 갱신한다.
