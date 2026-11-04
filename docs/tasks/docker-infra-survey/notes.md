# Docker 인프라 조사 작업 기록

## 2026-11-04 후속 사용자 정정

사용자는 정적 Svelte 구성을 요구하지 않으며, 일반적인 frontend/backend/DB 컨테이너 구성을 원한다고 명시했다. 기존 레포의 정적 배포 사례를 범용 기본 요구로 일반화하지 않는다. SvelteKit을 택할 때 adapter-node의 독립 Node 서버를 권장안으로 제시하되 SSR 강제·SvelteKit 의무화로 확대하지 않는다. 현재 결정과 통신/개발/운영 경계는 [구성 기준 보완](frontend-runtime-clarification.md)에 기록했다. 당시 완료 보고서·evidence 해시는 보존한다. 문서 보완만 수행하며 컨테이너 빌드·기동·E2E는 하지 않는다.

2026-11-04. 현재 요청은 다른 로컬 저장소 조사와 인프라 구성안 보고다. 다른 레포·원격 서버·Docker 상태는 변경하지 않는다. 하네스의 훅/Python 환경 변경은 다른 세션 소유이며 이번 변경에 포함하지 않는다.

## 확인한 실제 발견

- F1: `~/time-edu/stt-tts/deploy/docker-compose.yml:17`이 `frontend/Dockerfile`을 참조하지만 현재 파일이 없다. Compose의 frontend build 대상 경로를 계산해 `is_file() == false`를 확인했다. 이 compose를 그대로 재사용할 수 없다. 수정은 조사 범위 밖이며 report.md에서 후속 조치로 연결한다.
- F2: `~/start_n8n/docker-compose.yml`의 ybackend build context가 `~/hyeon_agent`를 가리키며 현재 디렉터리가 없다. 경로 계산과 `is_dir() == false`로 확인했다. 원래 호스트 의존성을 범용 기반으로 가져오지 않는다. 다른 레포 수정은 범위 밖이다.
- F3: `~/time-edu/ai-api-fastapi/deploy/prod/fastapi/fastapi.dockerfile:33`이 `.env`를 직접 COPY한다. build context의 `.env` 존재와 `.dockerignore` 미제외를 파일명/규칙만으로 확인했다. 이미지 빌드 시 로컬 환경 파일이 레이어에 포함되는 구성이다. 비밀값 내용·실제 배포 이미지 포함 여부는 조회하지 않았다. 런타임 주입으로 대체할 대상이며 다른 레포 수정은 범위 밖이다.
- F4: `~/rivendell/rivendell/backend/Dockerfile:21,38`은 build context 전체를 builder와 runtime에 복사한다. backend `.env`가 존재하고 root/Dockerfile 전용 ignore와 상위 ignore가 모두 없음을 확인했다. 해당 build context로 빌드하면 환경 파일이 runtime까지 복사되는 구성이다. 실제 이미지 빌드는 하지 않았다. 다른 레포 수정은 범위 밖이다.

## 반례와 제외한 의심

- `~/time-edu/test/infra/docker/docker-compose.yml`의 `context: ../..`는 정확히 레포 루트다. 잘못된 경로라고 보고하지 않는다.
- Rivendell의 PostgreSQL 18은 `PGDATA`를 명시적으로 예전 볼륨 하위로 설정한다. 기본 경로 변경만으로 데이터가 유실된다고 단정하지 않는다.
- 루트 사용자, latest 태그, healthcheck 부재 자체를 현재 실제 서비스 장애로 보고하지 않는다. 재사용 시 보완할 계약으로 구분한다.

## 검증 경계

탐색·정적 경로 대조·원문 읽기·로컬 Docker info/ps만 수행한다. 빌드·pull·up·exec·test·원격 명령은 실행하지 않는다. E2E는 구현 변경이 없어 해당하지 않는다. Docker 소켓 sandbox 거부 뒤 승인된 읽기 전용 조회로 데몬 정보를 확인했다.

## 최종 상태

- 보고서·인벤토리·원문 근거·로컬 관측을 작성했다. 57개 VCS 작업 사본/178개 파일/63종 해시이며 178개 파일을 다시 대조해 누락·변경이 없었다.
- 대표 Compose 6개 정적 config exit 0, doctor passed(exit 0), git diff --check exit 0. 기존 하네스의 누락된 과거 로컬 artifact note는 현재 검사로 승격하지 않았다.
- F1~F4는 report.md의 후속 담당/재사용 전 조건으로 연결한 범위 밖 항목이며 해결됐다고 보고하지 않는다.
- flow는 research:evidence에서 실제 수행/근거를 연결해 종료했다. task 완료는 별도 evidence verify/complete로 확인한다.
- 추가 변경은 docs/tasks/docker-infra-survey와 작업 인덱스의 한 행뿐이다. 다른 세션의 hooks/Python 변경을 수정하지 않았다.
