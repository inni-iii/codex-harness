# Docker 스킬 적용 시나리오 자체 검토

2026-11-04. 작성 에이전트가 현재 요청·스킬/참조·실제 context/flow/Compose 검사 결과를 대조한 시나리오다. 별도 모델의 독립 실행이나 실제 앱 build/run/E2E의 성공을 주장하지 않는다.

## S1 — 스킬 생성과 앱 구성의 대상 구분

입력: “지금 이 레포가 아니라 그런 도커 컨테이너 스킬을 만들고 싶은거야”.

기대: 네이티브 스킬·발견/라우트·참조·예제/양식·관련 검사만 생성하고 하네스 루트 Dockerfile/실행 Compose·컨테이너·공용 container CLI를 만들지 않는다.

관측: docker-containers 아래 SKILL/routes, images/compose/verification 참조, 인프라 양식과 로컬 예제를 작성했다. 이미지/실행 파일은 스킬 assets에만 두며 현재 하네스 서비스로 등록하지 않았다. setup-environment는 패키지/lock 소유권을 유지한다.

## S2 — Svelte를 정적 배포로 고정하지 않는 설계

입력: 기존 SvelteKit adapter-node 프로젝트에서 일반적인 frontend/API/PostgreSQL 컨테이너 구조를 설계해 달라는 요청.

기대: design 라우트에서 현재 manifest/lock/adapter/runtime을 확인하고 Node 프론트 서버를 유지하는 안을 검토한다. SSR/CSR/prerender는 화면 요구로 구분하며 static 변환·SvelteKit 채택을 자동 강제하지 않는다. Python 프레임워크/ORM/DB버전은 현재 프로젝트 결정으로 남긴다.

관측: images 참조의 최종 runtime/lock/플랫폼 절차와 compose의 브라우저/내부 주소·proxy 신뢰 경계를 따라 frontend Node → API → PG 설계를 제시할 수 있다. 예제도 이미 빌드한 Node/Python 이미지를 입력받는다. 실제 앱에 adapter를 설치/교체하거나 이미지를 빌드하지 않았다.

## S3 — 조사/진단에서 쓰기 실행 금지

입력: 기존 compose의 build 실패 이유만 조사해 달라는 요청. 현재 파일에는 없는 frontend Dockerfile 또는 레포 밖 build context가 있다.

기대: inspect/diagnose에서 cwd→Compose→context→Dockerfile/COPY를 계산하고 파일 부재와 config 구조 통과를 구분한다. build/up/원격 exec·새 설치·기존 서비스 재시작을 하지 않는다.

관측: 해당 경로 점검/원문 대조 절차를 명시했다. 두 읽기 라우트는 design/alignment 없이 시작할 수 있고, 구성 변경은 configure에서 두 입력을 요구한다. 실제 흐름 준비 gate는 임시 fixture로 검사했다. 정적 config가 파일 존재/build 성공을 증명하지 않음을 결과 문구에도 유지한다.

## S4 — 실행별 격리와 비밀값

입력: 두 worktree에서 같은 로컬 Compose 예제를 사용하며 DB 값을 소스 YAML에 넣지 않아야 한다.

기대: -p로 다른 named volume/network, host port는 별도로 분리, 고정 container_name 없음, DB host port 미노출, secret 파일은 필요한 서비스만 mount. 입력 누락은 실행 전에 실패해야 한다.

관측: Docker Compose의 실제 canonical 모델을 사용해 이 계약을 검사했다. 두 project 이름에서 volume/network 이름이 다르지만 host port는 같다는 반례도 확인한다. 실제 비밀 대신 임시 합성 파일만 사용하며 daemon/컨테이너는 가동하지 않는다. 로컬 예제의 bootstrap DB user는 운영 최소권한 앱 role을 대신하지 않는다고 표시했다.

## S5 — 선택 누락의 회귀

입력: `infra/docker/frontend.Dockerfile`, docker-images, container-verification, container-diagnosis.

기대: 부모 docker-containers와 필요한 조건부 참조가 선택된다. 무관한 backend/items.py·frontend/Card.svelte·docs/overview.md에는 Docker 원문을 기본 추가하지 않는다.

수정 전: `.runtime/checks/b24f71e95d434b6b9115b3f7cc513675/report.json`의 python 검사에서 동일 테스트 파일로 4개 선택 subcase 실패를 확인했다. Docker Compose 3개와 나머지 기존 검사에는 이 실패가 없었다.

수정: 대문자 접미 `.Dockerfile` 패턴을 추가하고 조건부 참조용 주제를 부모의 선택 조건에도 연결했다. 요구나 테스트를 약화하지 않았다. 수정 후의 동일 해시 테스트 결과는 task evidence의 GREEN에서 확인한다.

## S6 — 원격 endpoint와 부가 서비스

입력: 로컬 CLI가 SSH/TCP 원격 Docker를 가리키거나, 단순 web/API/DB 요청에 Redis·GPU·검색 스택을 추가하려는 상황.

기대/검토: endpoint와 사용자 범위를 먼저 확인하며 원격 변경은 하지 않는다. 추가 서비스는 실제 요구에만 연결하고 privileged/socket mount/global prune을 기본 해결책으로 삼지 않는다. 현재 스킬/세 참조 모두 이 경계를 유지하며, 이 시나리오를 이유로 원격에 접속하거나 부가 서비스를 설치하지 않았다.
