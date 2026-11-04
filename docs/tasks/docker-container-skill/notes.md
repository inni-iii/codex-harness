# Docker 컨테이너 스킬 작성 기록

2026-11-04. 현재 요청에 따라 다른 프로젝트에서 재사용하는 docker-containers 스킬을 만든다. 이 레포 자체의 Dockerfile/Compose·공용 container CLI·컨테이너 기동은 만들지 않는다. 이전 Docker 조사와 Svelte 정적 강제 금지 정정을 재사용하며 별도 요청/설계/정렬을 연결했다.

## 범위와 진행

- HEAD 2a955875 기준 detached worktree에서 수행한다. main의 hooks/Python 환경과 이전 조사 기록은 별도 세션/작업이며 최종 통합 시 최신 상태를 보존한다.
- 네이티브 skill create로 SKILL/context를 생성하고 images/compose/verification 조건별 원문, 프로젝트 양식과 로컬 예제를 추가했다.
- inspect/design/diagnose는 조사·설계이며 configure는 현재 design/alignment와 verify-work 호출을 요구한다. plan-project/검증/보안/문서 흐름을 연결한다.
- 스킬 자체가 flow catalog를 바꾸므로 생성 전 flow는 의도적으로 오래된 상태가 된다. 최종 계약에서 명시적으로 재시작하고 근거를 연결한다.
- alignment-template의 출력은 .runtime 경로가 필수임을 확인해 그곳에서 생성하고 현재 task의 검토 artifact로 연결했다. 이 명령 사용 오류는 앱/하네스 결함으로 기록하지 않는다.

## 검증 계획

context의 Docker 주제/경로 선택과 무관 작업 제외, 조건별 원문, configure 준비 gate·검증 경로, 실제 Compose canonical 결과/필수 입력 누락, 기존 flow/skill/선택 회귀를 확인한다. 요청별 실제 적용 자체 검토는 별도 시나리오 artifact에 남긴다. 서비스 코드 변경이 없어 앱 E2E는 수행하지 않는다. 예제 이미지 build/run도 미실행으로 명시한다.

## 첫 검증에서 확인한 항목

- F1: `infra/docker/frontend.Dockerfile`과 `docker-images`/`container-verification`/`container-diagnosis` 주제로 부모 스킬이 선택되지 않았다. 실제 등록 패턴/부모 topic 누락이며 요구 A2 위반이다. 자동 선택 회귀를 보존하고 수정한다.
- 첫 registered check: 415 tests, failure 7, skip 1. 이 중 선택 누락 4개 subcase가 F1이다. Compose 3개 실패는 fixture가 DOCKER_CONFIG를 빈 디렉터리로 바꿔 설치된 Compose 플러그인을 숨긴 환경 문제(`unknown shorthand flag: p`)이며 앱/Compose 결함으로 보고하지 않는다.
- 비밀 패턴 후보 3개는 secret 파일 경로/합성 fixture 경로의 오탐이다. 비밀값은 없으며 검사기를 약화하지 않는다. 예제의 런타임 파일 경로를 명시적 환경 입력으로 분리하고 fixture 이름을 분명히 한다.
- 최초 로그: `.runtime/checks/18e6e19d09e142848bd45f523bccf65e/`. 출력 크기를 줄이는 assertion/fixture 정리 뒤 선택 누락의 동일 테스트 해시로 RED/GREEN을 다시 보존한다.

- alignment는 실행기의 원래 .runtime 출력에 연결한다. docs 아래 임의 JSON은 검사 등록 대상이 아니어서 full plan이 needs_configuration을 반환했으며, 실행 근거를 소스에 잘못 분류하지 않도록 위치를 바로잡았다.

## 통합 전 검증과 반영

- 격리 worktree의 full_registered final 검사 4개 모두 통과: 415 tests, failure 0, skip 1. 원본 `.worktrees/docker-containers/.runtime/checks/dfb60f6bae174748a80d2cc3345a0b95/`를 보존한다.
- 원래 main에 22개 파일/문맥만 git apply로 반영했다. main의 MCP/웹 훅·Python/진단·이전 Docker 조사 변경을 보존했으며 staging/commit은 하지 않았다.
- 현재 통합 상태는 Docker 스킬/등록/검사의 실제 파일 경로로 등록 검사 4개를 다시 선택해 검증한다. 이전 조사 inventory/observations 같은 JSON artifact를 앱 코드 검사 등록으로 오인하지 않도록 현재 변경 경로를 명시한다.

## 최종 검증

- main 통합 후 `check --paths .agents/context.toml .agents/skill-flow.toml .agents/skills/docker-containers/SKILL.md .agents/skills/docker-containers/routes.toml .agents/skills/docker-containers/assets/compose.local.example.yaml tools/harness/tests/test_container_skill.py --checkpoint final`: 등록 검사4개 통과, 427 tests 실패0 skip1. 원본 `.runtime/checks/58215da2dd2c4e1c9ae46a158c013616/`. 신규 Docker 검사8개 모두 실행.
- skip은 기존 process-group signal 회귀의 sandbox 제약 subcase이며 Docker 검사가 아니다.
- F1의 동일 테스트 해시 RED는 worktree b24f71e95d434b6b9115b3f7cc513675, GREEN은 main 58215da2dd2c4e1c9ae46a158c013616이다. 선택·route·Compose 경계와 S1~S6을 재검토했다.
- F1 등록이 task 계약에 포함되므로 기존 alignment가 stale인 것을 확인하고 최신 계약의 ALIGN2를 작성했다. main flow를 maintain-skills → verify-work → docs sync/validation/index로 실제 증거와 연결해 종료했다.
- `git diff --check` 통과, main과 worktree의 새 스킬/검사8개 파일 내용 일치, 다른 세션의 웹검색 규칙/context 원문 보존 확인. 서비스 build/run·E2E는 수행하지 않았고 필요 이상의 재검사는 하지 않았다.

2026-11-04 사용자 승인된 연결 복구 후속: RED 원문과 동일 로그를 보존하고 입력에 쓰는 RED의 log 경로만 표준 .runtime/checks 보존 위치로 이관했다. RELOCATION/RED_ORIGINAL에 원래 task/review/보고서/로그 해시와 경로 변경을 보존했으며 workspace·소스·시각·실패 결과·기존 completed_at/리뷰 판단은 유지했다. 이관은 새 실행이나 독립 검토가 아니다. 현재 결과는 harness-connection-repairs에서 별도로 검증한다.
