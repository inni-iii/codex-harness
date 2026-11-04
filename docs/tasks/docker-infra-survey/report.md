# 로컬 저장소의 Docker 인프라 조사와 하네스 적용안

2026-11-04 조사. 현재 파일과 로컬 Docker 메타데이터에 대한 보고서다. 아래 구성안은 제안이며, 하네스에 Docker 실행 기능을 구현하거나 컨테이너를 가동한 결과가 아니다.

## 결론

현재 하네스에는 연구·설계·구현·검증 절차와 로컬 검사 실행기가 있지만, 서비스 전체를 Docker로 구성하는 공통 템플릿·실행/종료 도구·컨테이너 수용 검사는 없다. 기존 저장소의 구성에서 재사용할 패턴을 골라 **프로젝트별 서비스 인프라**와 **선택적인 검사 컨테이너**를 연결하는 것이 적절하다.

기본 서비스는 Svelte 프론트·Python API·PostgreSQL로 잡는다. Redis·백그라운드 워커·검색 DB·파일 저장소·GPU 워커·관측 스택은 실제 요구가 생긴 프로젝트에서 추가한다. Codex 대화창과 로그인까지 먼저 컨테이너 안으로 옮길 필요는 없다.

재사용 출발점은 zero-pod의 DB 준비 확인/워커 분리, Rivendell의 다단계 빌드/일반 사용자 실행/환경별 Compose, stt-tts의 선택 프로필과 의존성별 워커 격리다. 제품 경로·고정 이름/포트·비밀값 복사·원격 배포 코드는 가져오지 않는다.

## 조사 범위와 한계

- `/Users/inni`의 개발 소스 영역을 탐색했다. 1차 탐색은 62,588개 디렉터리이며 탐색 오류는 없었다. 이후 저장소 내부 `.claude/worktrees`를 추가 확인했다.
- 유효한 VCS 작업 사본은 **57개: 일반 Git 사본 37개, Git worktree 19개, SVN 사본 1개**다. 이 수에는 현재/이전 하네스 사본, 문서 생성용 복제본, 모델 미러, 중첩 저장소가 포함된다. 독립 서비스가 57개라는 뜻은 아니다. `.uv-cache`의 Git ignore 표식 3개는 저장소에서 제외했다.
- 이름 규칙으로 발견한 Docker 관련 파일은 **178개: Dockerfile 계열 106개, Compose YAML 46개, ignore 파일 26개**다. 내용 해시로 중복을 제거하면 63종이다. 추가 worktree의 40개 파일은 기존 63종과 내용이 같았다.
- `~/github/bloom-backend`는 VCS 표식이 없는 소스 사본이지만 Dockerfile/Compose/ignore 3개를 별도로 포함했다.
- `node_modules`, 가상환경, 패키지/빌드 캐시, 휴지통, 앱 번들, OS/사용자 Library의 일반 영역, 전역 플러그인 캐시는 제외했다. CloudStorage 전체 탐색은 완료하지 않았으며, 숨겨진 임의 저장 위치·임의 파일명 안의 모든 컨테이너 설정까지 찾았다고 주장하지 않는다. 외부 소스 디스크·원격 서버를 조사하지 않았다.
- `.env`·서비스 계정·Docker 인증 파일의 내용과 컨테이너 환경 변수는 읽지 않았다. 일부 `.env`는 존재 여부만 확인했다. 보고서에는 비밀값을 복사하지 않았다.
- Claude `projects`의 세션/하위 에이전트/관련 memory, Codex `sessions`/`archived_sessions`, 양쪽 history/index를 전체 검색 범위로 삼았다. 관련 원문을 읽었으며 아래의 원문 확인 날짜를 사용한다. `~/.claude/plans`는 없다. 2026년 3~9월 일부 Docker 논의는 history에만 남고 해당 세션 파일이 없어, 본문을 읽었다고 취급하지 않았다.
- 로컬 `info`/`ps`는 읽기 전용으로 조회했다. 다른 저장소 수정, 이미지 build/pull, 컨테이너 up/exec/stop/remove, 원격 접속은 하지 않았다.

파일별 경로·해시·저장소 분류는 [인벤토리](inventory.json), 명령/관측/원문 연결은 [근거](sources.md)에 있다.

## 이 노트북의 실제 Docker 스펙

| 항목 | 관측 결과 | 의미/한계 |
|---|---|---|
| 호스트 | MacBook Pro, Apple M5, 메모리 24GB | ARM 기반 개발 환경 |
| Docker Desktop | 4.59.1, build 217750 | 앱 plist 관측값; 지원 버전 인증은 아님 |
| Docker CLI | 29.8.0 | 클라이언트 버전 |
| Docker 서버 | 29.2.0, Docker Desktop, aarch64 | 로컬 VM의 서버 버전; CLI와 다름 |
| Docker Compose | 5.5.1 | 현재 명령/정적 검증에 사용 |
| Docker context | desktop-linux, 로컬 Unix socket | 원격 Docker가 아님을 확인 |
| VM 자원 | CPU 10개, 메모리 8,217,382,912 bytes ≈ 7.65GiB | 호스트 메모리 24GB 전체를 쓰는 것이 아님 |
| 저장소/제어 | overlayfs, cgroup v2 | 데몬 관측값 |
| 이미지/컨테이너 | 이미지 19개, 컨테이너 5개, 실행 중 0개 | 조사 시점의 상태 |
| 호스트 디스크 | APFS 데이터 볼륨 가용 약 437GiB | Docker VM 디스크 상한/사용량은 별도 미확인 |

정지 컨테이너는 zero-pod API·Drive worker·PostgreSQL 3개, 로컬 CI 도구 act 1개, deepwiki 1개다. 실행 중인 컨테이너가 없으므로 현재 사용량에서 서비스의 피크 메모리/성능을 추정할 수 없다. Compose에 적힌 메모리 제한 역시 실측 사용량이 아니다.

Mac에서는 일반 서비스 이미지를 `linux/arm64`로 우선 검증하고, 실제 배포 대상이 x86이면 `linux/amd64`도 별도로 검증해야 한다. 에뮬레이션은 네이티브와 성능이 같다는 근거가 아니다. NVIDIA CUDA 장치 요청이 있는 Spark 워커를 이 Mac의 일반 Docker GPU passthrough로 실행할 수 있다고 보지 않는다. Docker Model Runner의 별도 GPU 가속과도 구분한다. [멀티플랫폼 빌드](https://docs.docker.com/build/building/multi-platform/), [Desktop GPU 경계](https://docs.docker.com/desktop/features/gpu/).

## 저장소별 확인 결과

| 저장소/계열 | 현재 로컬 구성 | 재사용할 내용 | 그대로 채택하지 않을 내용 |
|---|---|---|---|
| `time-edu/zero-pod`, `test-zer-pod`, 관련 8개 worktree/외부 사본 | 로컬 PostgreSQL 16 + API + Drive worker. 운영 Compose는 API blue/green + 단일 worker, 외부 DB 사용. Python 3.11/uv | DB health 조건, API와 worker 실행 분리, 고정 lock 설치, 읽기 전용 자격 파일 마운트, 종료 유예 | 고정 container_name/5432/8000, Drive 제품 코드, 시작 시 seed/migration, 운영 호스트 경로, CPU 수로 자동 증가하는 worker 수, 원격 배포 코드 |
| `rivendell/rivendell` | PostgreSQL 18·Redis 8·Traefik·Prometheus·Grafana·Loki. base/dev Compose 분리. Python 3.12 다단계 이미지·일반 사용자 | 빌드/실행 단계 분리, 빌드 캐시, 일반 사용자, 관측 설정의 별도 관리 | `.env`까지 들어가는 전체 COPY(F4), 제품 도메인, 기본 전체 관측 스택, 기존 이미지 태그를 범용 권장 버전으로 고정 |
| `time-edu/stt-tts`, 루트 `stt-tts`, 복사본, `Downloads/stt-tts-dgx` | 이전 frontend/API/Redis/PG 구성과 현 serving/Spark 구성이 공존. Python 3.12 wrapper, CUDA/NGC/vLLM별 worker, 선택 profiles | 서로 다른 의존성의 프로세스/이미지 분리, `/ready` healthcheck, 모델 볼륨, 선택적 후보/벤치 실행 | 모든 AI worker 기본 기동, Mac에서 CUDA 실행 가정, --reload 운영화, 오래된 deploy Compose(F1), 고정 container_name과 과거 원격 실행 권한 |
| `ai-api-fastapi`, `ai-api-fastapi-test`, 루트 `ai-api-fastapi-test2`, 문서용 미러 | Python 3.12.3·uv 0.5.11, API blue/green 8003/8004, 외부 DB/파일 경로 | healthcheck와 단계적 교체의 개념 | `.env` COPY(F3), frozen 없는 sync, 제품 경로·운영 전제·고정 이름 |
| `time-edu/zero-error-backend` | Python 3.12 API + Redis, healthy 대기, 소스 전체 bind mount | 작은 Compose와 Redis 준비 확인 | uv latest, 전체 bind가 컨테이너 의존성을 덮는 구성, Redis를 모든 프로젝트의 필수로 지정 |
| `time-edu/test` | Next.js frontend·FastAPI·Celery·PG16·Redis7·Neo4j5·OpenSearch2.16·MinIO | API/worker 분리와 역할별 Dockerfile 배치 | Next.js 프론트를 Svelte 기반으로 복제, 전체 검색 인프라 기본 설치, 개발 서버의 운영 사용, `pnpm install --frozen-lockfile=false` |
| `github/penelope-backend`, `bloom-backend`, `.adalflow` 사본 | Elixir 다단계/일반 사용자 이미지, PG16·etcd·MinIO·Milvus·Attu | 다단계 빌드/일반 사용자라는 범용 원칙 | Elixir 런타임, Milvus 의존 묶음, 중복 고정 이름/5435/9000 등 제품 설정 |
| `start_n8n`, 중첩 qdrant/rustfs 저장소 | n8n·runner·backend·PG·RustFS·Qdrant, 선택적 MCP/Triton/Gemma. 여러 latest 태그 | 필요한 서비스만 켜는 프로필, 파일/검색/모델 역할 분리 | n8n/MCP/GPU를 기본 의존성으로 도입, 존재하지 않는 ybackend 컨텍스트(F2), 고정 포트/이름, latest 기본값 |
| `time-edu/mitam-math`, test 사본/6개 worktree | 서비스 Dockerfile/Compose 없음. systemd OCR·생성 worker. 정적 Svelte. 결제 worktree에는 로컬 Docker 임시 PG 검사 실행기 | 로컬 Unix Docker만 허용, 임시 DB·동적 loopback 포트·합성 데이터·준비 대기·자기 자원 정리의 검사 원칙 | 앱 전체가 이미 컨테이너화됐다고 표현, 운영 systemd 역할·스케줄러를 누락, 결제 특화 스키마/명령을 범용화 |
| `time-edu/ax-hub`, perf worktree | Svelte adapter-node, `app-dev.yaml`/`app-prod.yaml`과 실제 workflow는 `gcloud app deploy` | Svelte의 Node 서버 배포 분기 | CLAUDE.md의 EC2/IDC Docker 설명을 실제 배포로 오인; 이번에 클라우드 상태는 조회하지 않음 |
| `inni/sketch-kit` | React/Vite·Python, Docker 파일 없음 | 기존 manifest/lock에 맞는 환경 선택 | React 구성을 하네스의 Svelte 기본으로 대체/복사 |
| 나머지 Git/SVN/미러/도구 저장소 | `spec-kit-test`, `stt-tts-api`, `zero-error-claude-package`, `svn-mpod2`, `mpod2-backend`, `hello-world`, `math-ilta-svelte`, `260305_stt-tts`, `stt`, 모델 미러, `.openclaw/workspace`, 현재/이전 하네스 등 | 필요한 선언/운영 원문만 선택 | Docker 파일이 없다는 사실을 Docker 실행 가능성 또는 불가능성의 증명으로 확대하지 않음 |

`docker-patterns`·`devops-engineer` 원문과 Compose 참조도 확인했다. 다단계 빌드·볼륨·네트워크 분리·복구 질문은 참고할 수 있지만, 제품명·고정 스택·항상 4 worker·GitHub CI/CD·SSH 배포·서버 보안 변경은 현 하네스에 그대로 이식하지 않는다. 템플릿 내부에도 latest를 금지하면서 latest 이미지를 쓰거나 개발 watch를 운영 예제에 섞는 부분이 있어 실제 구성의 정본으로 삼지 않는다.

## 확인한 결함과 후속 조치

다른 저장소의 수정은 현재 조사 요청 범위 밖이다. 아래는 해결 완료가 아니라 재사용 전 처리할 항목이다. 비밀값의 유효성·이미지 배포 이력은 시험하지 않았다.

| ID | 재현 근거 | 영향 | 후속 담당/다시 확인할 조건 |
|---|---|---|---|
| F1 | `time-edu/stt-tts/deploy/docker-compose.yml:17`의 `frontend/Dockerfile`이 현재 없음 | 해당 frontend build 대상은 그대로 사용할 수 없음 | STT 저장소 담당: 이전 deploy 경로를 사용할 때 현 serving 구조와 정리하고 실제 build 검증 |
| F2 | `start_n8n/docker-compose.yml`의 ybackend context `../hyeon_agent` 디렉터리가 없음 | 현재 노트북에서 전체 기본 구성 build가 재현되지 않음 | n8n 저장소 담당: 서비스가 필요한지 결정 후 레포 내부 경로/선택 프로필로 정리 |
| F3 | `ai-api-fastapi/deploy/prod/fastapi/fastapi.dockerfile:33`의 `.env` COPY + 컨텍스트에 `.env` 존재 + ignore 미제외 | build 시 환경 파일이 이미지 레이어에 포함되는 구성 | API 저장소 담당: 런타임 주입으로 변경, 빌드 비밀은 BuildKit secret 사용, 새 이미지의 파일/레이어를 검사 |
| F4 | Rivendell `backend/Dockerfile:21,38`의 전체 COPY + backend `.env` 존재 + root/Dockerfile 전용 ignore 없음 | 해당 context로 build하면 `.env`가 builder와 최종 runtime에 포함되는 구성 | Rivendell 담당: `.dockerignore`/복사 범위 보완 후 실제 최종 이미지와 레이어 검사 |

정적 경로 대조는 F1/F2의 파일/디렉터리 부재를 확인한다. F3/F4는 Docker COPY/ignore 계약과 현재 파일 존재를 대조한 결과이며 실제 이미지를 빌드해 노출을 재현하지 않았다. [빌드 컨텍스트](https://docs.docker.com/build/concepts/context/), [빌드 비밀](https://docs.docker.com/build/building/secrets/).

반대로 `time-edu/test`의 `infra/docker`에서 `context: ../..`는 올바르게 레포 루트로 해석된다. Rivendell PostgreSQL 18은 PGDATA를 명시적으로 지정하고 있어 기본 경로 변경만으로 장애라고 판정하지 않았다. 고정 포트/이름은 동시에 다른 사본을 기동할 때 충돌하는 조건이지, 현재 정지 상태에서 서비스 장애를 재현한 것은 아니다.

## 권장 서비스 인프라 계약

### 최소 구성과 선택 구성

```text
브라우저
  └─ web 또는 proxy
       ├─ Svelte 정적 파일 또는 Node SSR
       └─ /api → Python API → PostgreSQL
                         └─ 필요한 경우 worker / queue / storage

검사 시: 별도 test project의 DB + API + web + 일회성 E2E runner
```

| 역할 | 기본 적용 | 계약 |
|---|---|---|
| web | 필수 역할 | static/Node SSR를 프로젝트에서 선택. 개발 Vite 서버와 운영 빌드를 구분 |
| API | 필수 역할 | 프로젝트가 정한 Python·프레임워크·lock. 일반 사용자, 종료 신호 전달, 상태 확인 |
| PostgreSQL | 기본 DB | 프로젝트 버전/확장 선택, named volume, 준비 확인, 전용 앱 권한, 백업/복구 계약 |
| migration | 스키마 변경 시 | 일회성 실행·성공 확인·중복 방지. 모든 API/worker 부팅마다 무조건 실행하지 않음 |
| worker / Redis | 필요 시 | 실제 비동기 요구/내구성에 따라 추가. 같은 앱 이미지의 다른 명령을 우선 검토 |
| object/vector/search DB | 필요 시 | 파일·검색 요구와 PostgreSQL 확장 가능성을 확인한 뒤 선택 |
| GPU worker | 필요 시 별도 대상 | 호스트/아키텍처/드라이버·CUDA·모델 라이선스와 자원 계약을 별도로 검증 |
| E2E / harness runner | 검사 시 | 일회성·별도 프로젝트·합성 입력·JUnit/trace 출력. 앱 컨테이너와 분리 |
| 관측 도구 | 필요 시 | 기본 stdout/stderr·요청 ID·회전 정책. Prometheus/Grafana/Loki는 요구가 있을 때 |

Redis, Qdrant, Neo4j, OpenSearch, Milvus, MinIO, n8n은 현재 공통 필수 스택으로 확정하지 않는다. Kubernetes·클라우드 IaC·원격 배포·GitHub CI도 이번 구성의 선행 조건으로 추가하지 않는다.

### 반드시 구분할 실행 계약

1. **환경**: 공통 Compose와 명시적인 dev/test/prod override. 운영에 소스 bind·--reload·디버그 포트를 섞지 않는다. 프론트 정적 파일에는 브라우저 공개 설정만 들어가며 서버 비밀은 주입하지 않는다.
2. **격리**: 프로젝트/worktree/test 실행별 `-p` 이름, 개별 volume과 포트. 고정 container_name은 없애고 서비스 DNS를 사용한다. `-p`만 바꿔도 동일한 host port 충돌까지 해결되는 것은 아니다. [프로젝트 이름](https://docs.docker.com/compose/how-tos/project-name/).
3. **노출**: 개발 포트는 loopback에 바인딩. DB는 기본 host port 없이 내부 통신하고 디버깅에 필요한 경우에만 loopback override. 브라우저의 API 주소와 컨테이너 내부 API 주소를 구분한다.
4. **준비/복구**: live/ready 동작을 실제 앱에서 정의하고, DB `service_healthy`와 migration `service_completed_successfully` 뒤 앱을 시작하는 방식을 검토한다. 시작 순서는 런타임 재연결을 대신하지 않으며 unhealthy 상태 자체가 자동 재시작을 뜻하지 않는다. [시작 순서](https://docs.docker.com/compose/how-tos/startup-order/).
5. **빌드**: manifest/lock을 먼저 복사하고 프로젝트에 맞는 frozen install, 빌드/실행 단계 분리, 버전/플랫폼 고정, 일반 사용자 실행. 호스트 `.venv`·node_modules·.env·키·세션·Git 메타데이터를 이미지에 복사하지 않는다.
6. **비밀**: 로컬 개발의 비밀 파일과 공유 가능한 example을 구분한다. 운영은 서비스별 파일 secret 주입 등을 선택한다. Compose secret은 호스트 파일을 mount하는 방식이므로 비밀 저장소 전체를 대신하지 않는다. `_FILE` 지원은 앱/이미지에서 확인한다. [Compose secrets](https://docs.docker.com/compose/how-tos/use-secrets/).
7. **저장/스키마**: DB/data/upload/model 볼륨은 이미지와 분리한다. 초기화 SQL은 기존 DB의 스키마 갱신 도구가 아니다. DB 메이저 버전과 볼륨 경로, 확장, migration·백업·복원 절차를 함께 고정한다. PG18 이상의 기본 데이터 경로 변경을 버전 선택 시 확인한다. [PostgreSQL 공식 이미지](https://hub.docker.com/_/postgres).
8. **자원**: CPU/메모리/프로세스/로그 한도와 worker 수를 설정한다. 호스트 CPU 개수로 worker 수를 자동 증폭하지 않는다. app worker 수 × DB pool 상한과 blue/green 공존 자원까지 산정한다.
9. **선택 서비스**: core는 기본으로 두고 debug/worker/관측/벤치 등만 profile로 관리한다. 선택된 서비스의 의존 프로필도 일관되게 활성화되는지 검증한다. [프로필](https://docs.docker.com/compose/how-tos/profiles/).
10. **운영 복구**: 앱 이미지 교체와 데이터 migration을 구분한다. 이전 이미지로의 복귀가 파괴적 migration의 복구를 보장하지 않는다. 볼륨 보존, 별도 복원 DB에서 backup 검증, 종료 유예를 실제로 확인한다.

### 이 노트북의 초기 자원 예산 제안

현재 VM 약 7.65GiB를 기준으로, 개발 스택은 우선 다음 범위에서 검증할 수 있다. 이는 실측 사용량·운영 sizing·확정 제한이 아니다.

| 역할 | 초기 메모리 상한 검토값 | 비고 |
|---|---|---|
| PostgreSQL | 1GiB | 테스트 데이터·동시성·확장에 따라 재산정 |
| Python API | 1GiB | 개발 1 worker부터 시작, DB pool과 함께 조정 |
| Svelte 개발 서버 | 1GiB | 실제 빌드/개발 피크 별도 측정 |
| 선택 worker/Redis | 합계 0.5~1GiB | 필요할 때만 활성화 |
| 일회성 E2E runner | 1~2GiB | 검사 때의 추가 예산; 동시 build를 피하고 전체 피크 측정 |

GPU·대형 검색 DB·전체 관측 스택을 함께 올리는 예산은 아니다. Docker 설정을 이번 조사에서 변경하지 않았다.

## 하네스에 연결할 위치와 구현 순서

아래 경로는 제안이다. 이번에 생성하지 않았다.

```text
.agents/skills/setup-environment/references/containers.md   로컬 컨테이너 준비·기동·종료 절차
.agents/skills/setup-environment/assets/containers/        검토한 최소 양식
tools/harness/harness/containers.py                        공용 실행 기능이 필요할 때 추가
docs/projects/<프로젝트>/infrastructure.md                 해당 서비스의 결정·자원·운영 계약
docs/projects/<프로젝트>/workflow.toml                     읽기 조건과 실제 검사 명령
infra/compose*.yaml, 프로젝트별 Dockerfile                 서비스를 시작할 때 배치 결정
.runtime/<작업>/                                          검사 보고서·JUnit·trace
```

새 독립 인프라 스킬을 곧바로 늘리기보다 setup-environment에 컨테이너 절차를 보완하고, python-backend/Svelte/Postgres/security-review/e2e-testing/verify-work의 기존 책임으로 연결하는 안을 우선 검토한다. 규모가 커져 별도 책임이 생기면 maintain-skills 절차로 분리한다. 현재 `environment inspect/install`은 패키지 선언/lock 도구이며 Docker lifecycle을 이미 수행한다고 표현하지 않는다.

1. **계약 결정**: 서비스 실행 인프라를 우선한다. 하네스 실행 자체까지 컨테이너화할지, 프로젝트 프레임워크·Svelte static/SSR·DB 버전/확장·운영 대상·데이터 요구를 결정한다.
2. **최소 양식**: web/API/PG, dev/test/prod 차이, 이름/포트/볼륨 격리, 런타임 secret과 이미지 제외 규칙을 만든다. 실제 앱이 없을 때는 서비스 템플릿과 미확정 입력으로 표시한다.
3. **대표 로컬 사례**: 새 소형 프로젝트/fixture에서 실제 빌드→기동→준비→저장/재조회→재기동 후 데이터 유지→자기 자원 정리를 검증한다. 기존 사용자 컨테이너를 사례로 재사용/변경하지 않는다.
4. **실패/격리 검증**: DB 지연·migration 실패·API 재연결·포트 충돌·누락 secret·동시 worktree 두 개·timeout/SIGINT 정리를 검증한다. 실패를 숨기거나 전역 prune/down -v로 정리하지 않는다.
5. **공용 도구 연결**: 실제 필요가 확인되면 inspect/plan/up/down 등의 인터페이스와 project workflow 계약을 구현한다. 로컬 endpoint만 허용하고 명시한 프로젝트 자원만 조작하며, 기본 읽기 조회와 변경 명령을 구분한다. 명령 이름/계약은 아직 미구현이다.
6. **검사 runner**: Python/Node/Playwright 환경을 고정한 선택 runner를 연결한다. Codex 인증·개인 세션·SSH 키를 이미지에 넣지 않고 Docker socket을 앱/검사 컨테이너에 기본 mount하지 않는다. 호스트가 Compose를 제어하고 runner는 테스트 네트워크와 결과 디렉터리만 쓰는 방식을 우선 검토한다.
7. **운영 명세**: 백업/복구·자원 피크·이미지 식별·TLS/프록시·배포/롤백을 프로젝트별로 검증한 뒤 운영 담당자에게 전달한다. 상시 지시상 SSH 서버 변경은 별도 금지 경계로 유지한다.

컨테이너 runner는 macOS 기본 Python/Expat 조합 문제에 덜 의존하는 Linux 검사 환경을 제공할 수 있지만, 호스트의 Python 설치를 복구했다는 뜻은 아니다. staged/snapshot/worktree 검사에 Git 메타데이터·경로·실행 권한이 필요한 점도 별도 설계/검증해야 한다.

## 이번 검증과 남은 일

- 178개 파일의 원문을 읽어 구조를 추출하고 해시로 중복을 비교했다. 원문의 모든 주석·실행 행동을 의미적으로 전수 검증한 것은 아니다.
- 대표 Compose 6개 조합은 환경 파일/보간을 해제한 `config --quiet` 정적 검증에서 모두 종료 코드 0이다. 이는 문법/구조 확인이며 missing Dockerfile/context나 실제 build/start 성공을 증명하지 않는다.
- 실제 Docker daemon의 아키텍처·자원·상태를 조회했다. 5개 컨테이너의 상태는 모두 exited였다.
- Docker build, 이미지 내부 비밀값 검사, 실행/성능/복구/E2E는 이번에 수행하지 않았다. 다른 저장소와 원격은 변경하지 않았다.
- 현재 결정할 사항은 서비스의 첫 대표 사례, static/SSR, Python/Node/DB 버전과 확장, 운영 환경, 필요한 비동기/저장소, 하네스 runner 범위다. 이들을 결정하기 전에 다른 레포의 전체 스택을 기본값으로 가져오는 것은 추천하지 않는다.

이 보고서의 완료는 조사·구성안 전달의 완료다. 컨테이너 인프라 구현·검증 완료와 구분한다.
