# 조사 근거와 재현 조건

확인일: 2026-11-04. 작성자 자체 조사이며 독립 에이전트 평가를 수행하지 않았다.

## 로컬 관측

작업 디렉터리: `/Users/inni/inni/codex-harness`. 다른 저장소는 읽기 전용으로 확인했다.

- 홈 소스 탐색 및 `.claude/worktrees` 추가 탐색: 57개 유효 VCS 작업 사본과 Docker 관련 178개 파일/63종 해시. 파일별 경로/해시는 inventory.json에 보존한다. `.git` 문자열만 있는 `.uv-cache`의 표식 3개는 제외했다.
- Dockerfile/Compose/ignore 원문은 Python 표준 파일 읽기와 Ruby `YAML.safe_load(..., aliases: true)`로 읽었다. 외부 YAML 객체 생성·환경 보간·앱 코드 실행은 하지 않았다. 프로그램은 `/private/tmp/docker-infra-analyze.py`였고 공용 의존성으로 추가하지 않았다.
- `docker --version`: 29.8.0, exit 0. `docker compose version`: 5.5.1, exit 0.
- `docker context show`: desktop-linux, exit 0. `docker context inspect desktop-linux --format '{{.Endpoints.docker.Host}}'`: 로컬 unix socket, exit 0.
- sandbox의 `docker info`/`docker ps`는 socket 접근 거부로 exit 1이었다. 이를 0개 컨테이너의 증거로 쓰지 않았다. 이후 승인된 읽기 전용 같은 daemon 조회가 exit 0이었다.
- `docker info`의 allowlist 필드: server 29.2.0, Docker Desktop, aarch64, 10 CPU, memory 8217382912 bytes, containers 5/running 0, images 19, overlayfs, cgroup 2.
- `docker ps -a`의 이름/이미지/상태/포트만 조회: zeropod-drive-worker, zeropod-api, zeropod-db, act test container, deepwiki container 모두 exited. inspect의 환경 변수·인증·로그는 조회하지 않았다.
- `system_profiler SPHardwareDataType -json`에서 모델/칩/메모리만 보고서에 사용: MacBook Pro, M5, 24GB. 장치 식별자는 산출물에 보존하지 않았다.
- `/Applications/Docker.app/Contents/Info.plist`: 4.59.1/build 217750. `df -h /Users/inni`: host APFS available 약 437GiB. Docker VM disk quota/사용량은 미조회.

## 대표 원문 위치

모든 `~` 경로는 조사한 이 노트북의 출처다. 다른 노트북에서 반드시 존재하는 하네스 의존성이 아니다. 전체 파일을 레포에 복제하지 않는다.

| 주장 | 읽은 원문 |
|---|---|
| DB healthy와 API/worker 분리 | `~/time-edu/zero-pod/docker-compose.local.yml:14,40,45,63` |
| 운영 이미지의 frozen uv와 비밀 파일 런타임 주입 | `~/time-edu/zero-pod/backend/deploy/prod/fastapi/fastapi.dockerfile:28`, `backend/docker-compose.yml:24` |
| API 시작 시 migration 실행 | `~/time-edu/zero-pod/backend/deploy/prod/fastapi/run.sh:5` |
| 다단계/일반 사용자와 전체 COPY | `~/rivendell/rivendell/backend/Dockerfile:7,21,26,38,43` |
| PG18/Redis8/관측 도구, 명시 PGDATA | `~/rivendell/rivendell/infrastructure/docker-compose.yml:7,15,25,36,48,64,78` |
| GPU worker/profile/모델 볼륨 | `~/time-edu/stt-tts/deploy/spark/docker-compose.yml`, `serving/workers/*/Dockerfile*` |
| 이전 frontend Dockerfile 누락 | `~/time-edu/stt-tts/deploy/docker-compose.yml:17` 및 현재 경로 부재 |
| ybackend의 없는 host context | `~/start_n8n/docker-compose.yml` 및 `~/hyeon_agent` 경로 부재 |
| 환경 파일 이미지 COPY | `~/time-edu/ai-api-fastapi/deploy/prod/fastapi/fastapi.dockerfile:33`, `.dockerignore`, `.env` 존재 여부 |
| 실제 프론트 배포 변형 | zero-pod/mitam `frontend/svelte.config.js`의 adapter-static; ax-hub `svelte.config.js`의 adapter-node와 `app-*.yaml`/`.github/workflows/deploy*.yml`의 App Engine deploy |
| systemd worker와 Docker PG 테스트 분리 | `~/time-edu/mitam-math/backend/ops/*.service`, `.claude/worktrees/toss-credit-recovery/backend/tests/credit_recovery_pg_runner.py:124,437` |
| 템플릿에서 선별할 원칙과 제외할 운영 권한 | `~/time-edu/mitam-math/.claude/skills/docker-patterns/SKILL.md`, `devops-engineer/SKILL.md`, `devops-engineer/references/docker-compose-infra.md` |

## 정적 Compose 검증

명령 형태: `docker compose --env-file /dev/null -f <절대경로> [추가 -f] config --no-interpolate --no-env-resolution --quiet`.

프로젝트 환경 변수 값과 env_file 내용을 읽지 않도록 위 옵션을 사용했다. Docker daemon에 시작/중지 명령을 보내지 않았다. 모두 exit 0, stderr 비어 있음.

1. zero-pod `docker-compose.local.yml`.
2. Rivendell `infrastructure/docker-compose.yml` + `docker-compose.dev.yml`.
3. stt-tts `deploy/docker-compose.yml`.
4. stt-tts `deploy/spark/docker-compose.yml`.
5. time-edu/test `infra/docker/docker-compose.yml`.
6. start_n8n `docker-compose.yml`.

정적 config는 Dockerfile/context 존재 검사나 실제 기동 시험을 대신하지 않는다. F1/F2는 config exit 0 상태에서도 별도 파일시스템 대조로 확인됐다. 기존 컨테이너나 DB에 실험하지 않았다.

## 공식 원문과 채택 범위

아래 페이지를 직접 열어 본문을 읽었다. 기술 설명은 이 원문과 현재 로컬 파일을 대조한 판단이다. 예제의 모든 버전·스택을 채택한 것은 아니다.

| 원문 | 확인한 계약/적용 |
|---|---|
| [시작 순서](https://docs.docker.com/compose/how-tos/startup-order/) | 단순 running과 ready는 다르다. healthy 대기와 일회성 성공 대기를 분리한다. |
| [프로필](https://docs.docker.com/compose/how-tos/profiles/) | core/선택 서비스 구분, 명시 대상 서비스와 의존 프로필의 활성 조건. |
| [프로젝트 이름](https://docs.docker.com/compose/how-tos/project-name/) | 독립 환경의 프로젝트 이름과 우선순위; host port 분리는 별도다. |
| [빌드 컨텍스트](https://docs.docker.com/build/concepts/context/) | COPY/ADD의 범위, context root와 Dockerfile 전용 ignore. F3/F4 판단 근거. |
| [빌드 비밀](https://docs.docker.com/build/building/secrets/) | 빌드 secret mount를 일반 ARG/ENV와 구분. 런타임 비밀도 COPY하지 않는 구성 제안. |
| [Compose secrets](https://docs.docker.com/compose/how-tos/use-secrets/) | 서비스별 파일 mount, `_FILE`는 지원 이미지/앱의 관례. Swarm 필수라는 템플릿 문구를 그대로 채택하지 않음. |
| [멀티플랫폼](https://docs.docker.com/build/building/multi-platform/) | arm64/amd64 분기와 에뮬레이션 비용. |
| [Desktop GPU](https://docs.docker.com/desktop/features/gpu/) | 일반 Linux 컨테이너의 NVIDIA passthrough와 다른 플랫폼 Model Runner 가속을 구분. |
| [PostgreSQL 공식 이미지](https://hub.docker.com/_/postgres) | 지원 아키텍처, 초기화/PGDATA/18 이상 볼륨 변화. 조사 시 태그 목록을 전역 기본 버전으로 고정하지 않음. |

## 과거 원문 확인과 누락

아래 원문 날짜는 저장된 UTC timestamp 기준이다.

- Codex 2026-10-30 원문 `rollout-2026-10-20T12-16-08-01a1574f-2aae-7f03-bec3-73a54325a0e4.jsonl`의 스킬 선별 답변: docker-patterns는 보안 참고 일부만 반영했고, 전체 컨테이너/배포 스택은 미이식이었다. 현재 파일과 대조했다.
- Codex 2026-10-20~30 원문 `rollout-2026-10-20T14-34-13-01a157cd-9469-7332-bc86-682121960fcb.jsonl`: mitam의 API/복구/systemd timer 역할 구분. 현재 운영 동작은 재실측하지 않았다.
- Claude 2026-09-14 원문 `stt-tts/83937562-faa5-480c-96f9-746099df46a4.jsonl`: 컨테이너를 여러 개 사용하는 이유와 모델/라이브러리 의존 분리 질문을 읽었다. 과거 메모리 수치를 현재 Mac 자원으로 재사용하지 않았다.
- Claude 2026-10-16/20/27 원문 `toss-credit-recovery/1513e60f-5999-4496-b720-45d7e6e1a375.jsonl`: systemd/API/worker 질문과 로컬 PG 검사 관측을 읽었다. 현재 실제 검사 실행은 하지 않았다.
- 양쪽 history/index에서 2026년 3~9월 Docker/인프라 대화도 찾았다. Codex `019fd21c...`, `019c940e...`, `01a08e6a...`, `01a15290...`, Claude `bedbfda7...`, `d57c826b...`, `04fa57e2...` 등 일부 본문 파일은 접근 가능한 보관 경로에 없었다. history는 탐색 보조로만 사용했다.

현재 사용자 지시가 과거 실행 권한보다 우선한다. 원격 서버에는 읽기 전용 제약을 유지했고 이번에는 접속 자체를 하지 않았다.
