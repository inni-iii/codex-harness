# Compose·네트워크·저장·수명

여러 컨테이너의 topology, 환경 차이, 데이터/복구와 운영 명령을 설계·작성할 때 읽는다. 대상 프로젝트 문서가 구체적인 정본이며 이 문서는 작업 방법이다.

## topology와 환경

프론트·API·DB 등 실제 프로세스를 서비스로 나눈다. 같은 코드 이미지의 API/worker는 다른 command로 재사용할 수 있다. 별도 라이브러리/하드웨어/배포 수명이 필요하면 이미지를 나눈다. 모든 프로젝트에 queue·vector DB·object storage·관측 스택을 한꺼번에 넣지 않는다.

공통 Compose와 명시적인 dev/test/prod override를 검토한다. auto-loaded override, 여러 파일의 경로 기준과 merge 결과를 확인한다. dev의 소스 bind/--reload/디버그 포트가 운영 설정에 남지 않게 한다. 선택 서비스에 profile을 쓰되 필요한 dependency/profile 조합도 확인한다.

서비스용 예제는 [로컬 양식](../assets/compose.local.example.yaml)에 있다. 이 양식은 사용자 앱을 자동 생성하지 않는다. 이미지·Node/Python 실행·상태 endpoint·DB 설정의 계약을 채우고 프로젝트에서 확인한 뒤 사용한다. 운영 전용 role·프록시·TLS·backup/복구는 별도 설계한다.

## 네트워크와 주소

- 같은 네트워크에서는 서비스 이름으로 통신한다. 컨테이너 안 localhost는 그 컨테이너 자신이다. 브라우저 공개 URL과 서버 간 내부 URL을 나눈다.
- 외부 진입은 frontend/proxy에 모으고 DB 포트는 기본적으로 내부에 둔다. 개발 직접 접근은 loopback의 명시적 포트로 제한한다. expose는 방화벽이나 권한 검사가 아니다.
- 공개/데이터 네트워크를 필요한 경계에 따라 나눈다. API가 외부 서비스도 부르면 egress 가능한 네트워크가 필요하다. internal 네트워크와 DB host port 공개를 함께 써 안전하다고 단정하지 않는다.
- 프록시를 쓰면 path rewrite·origin·forwarded header 신뢰·쿠키/세션·HTTPS/WebSocket/스트림 timeout을 확인한다. frontend가 있어도 API의 실제 자원 권한 검사를 대체하지 않는다.

## 준비·migration·재연결

DB healthcheck와 `depends_on.condition: service_healthy`는 시작할 때의 준비 대기다. schema migration이 필요하면 프로젝트의 실제 도구로 일회성 성공/실패를 확인한 뒤 app/worker를 시작한다. `service_completed_successfully`가 맞는 경우 사용한다. ORM이나 Alembic을 스킬이 정하지 않는다.

마이그레이션을 모든 API replica/worker의 boot마다 무조건 실행하지 않는다. 초기 데이터/역할 생성과 기존 DB 업그레이드, test seed를 구분한다. `/docker-entrypoint-initdb.d` 스크립트는 비어 있는 데이터 디렉터리의 초기화에 사용되며 기존 DB의 스키마 수정 대체물이 아니다.

런타임 DB 중단·재연결·재시도/마감·worker 중복 처리는 앱에서도 다뤄야 한다. unhealthy 표시만으로 자동 재시작한다고 가정하지 않는다. restart 정책·정상/비정상 종료·운영 복구를 별도로 확인한다.

## 데이터·비밀·자원

- DB/upload/model 등 영속 데이터는 이미지와 분리한다. named volume의 소유자·프로젝트 범위·데이터 버전·쓰기 권한을 정한다. read-only 모델/참조와 writable cache를 구분한다.
- PostgreSQL의 이미지 버전/확장·PGDATA/volume 경로를 함께 고정한다. 특히 18 이상 기본 경로 변경, 명시 PGDATA, 기존 메이저 버전 데이터를 대조한다. tag만 바꿔 upgrade하지 않는다.
- dev 전체 mount가 컨테이너 `.venv`/node_modules를 덮거나 호스트 native 라이브러리를 가져오지 않게 source 하위 경로/전용 volume/watch 등 프로젝트에 맞는 방식을 선택한다.
- 비밀은 이미지/COPY/공유 YAML에 넣지 않는다. 서비스별 secret 파일 또는 검토한 런타임 주입을 사용한다. `_FILE` 지원은 해당 앱/이미지에서 구현돼 있어야 한다. Compose secret은 호스트 파일 권한 관리와 비밀 교체/보관을 대체하지 않는다.
- POSTGRES_USER로 생성하는 bootstrap role은 superuser다. 로컬 예제와 운영 앱 최소권한 role을 구분한다. 앱용 role·migration role·backup 권한은 프로젝트에서 설계한다.
- CPU/메모리/pids·worker 수·DB pool·로그 회전 한도를 정하고 runtime에서 적용 여부를 확인한다. host/VM 자원과 container 한도, 실측 피크를 구분한다. 호스트 CPU 수만으로 worker를 늘리지 않는다.

## 실행 격리와 정리

실제 명령은 대상 레포 루트에서 실행한다. 아래 `example-dev`와 Compose 파일명은 해당 프로젝트의 값으로 바꾸며, 변경 명령은 현재 요청이 허용한 로컬 구성 작업에서만 수행한다. 도구/파일 지원과 입력·secret 준비를 먼저 확인한다.

```sh
docker context show
docker context inspect --format '{{.Endpoints.docker.Host}}'
docker compose -p example-dev -f compose.yaml -f compose.dev.yaml config --quiet
docker compose -p example-dev -f compose.yaml -f compose.dev.yaml build web api
docker compose -p example-dev -f compose.yaml -f compose.dev.yaml up -d --wait --wait-timeout 120
docker compose -p example-dev -f compose.yaml -f compose.dev.yaml ps
```

`config`는 실제 환경의 비밀값을 출력하지 않는 validation이지만 존재하는 env/secret을 해석할 수 있다. 순수 정적 원문 검사는 verification 절차의 보간 해제 옵션을 쓴다. 위 서비스 이름·build/health·프로필은 예시이며 조회만 요청받았다면 build/up을 실행하지 않는다. 예제 asset은 이미 빌드한 image를 받으므로 build 명령을 그대로 적용하지 않는다.

실행/worktree마다 고유한 `-p` 이름·호스트 포트·volume·결과 경로를 쓴다. 고정 container_name, external volume, 고정 top-level volume name은 project prefix 격리를 무력화할 수 있다. `-p`는 같은 host port 충돌을 해결하지 않는다.

명령 전 cwd·Compose 파일·project·endpoint·기존 자원과 계획을 확인한다. info/ps/config 조회와 build/pull/up/run/down 변경을 구분한다. 로컬 build/up 요청은 해당 프로젝트의 허용된 로컬 자원에 한정한다. remote endpoint에서 같은 명령을 재실행하지 않는다.

timeout/SIGINT/실패에도 **이번 실행이 만든 자원만** 정리하고 결과/종료 코드를 보존한다. 기존 volume·다른 프로젝트·공유 model cache를 삭제하지 않는다. down -v/global prune을 기본 복구로 쓰지 않는다. 볼륨 보존과 별도 DB로의 backup restore를 실제 확인하며 앱 image rollback과 데이터 rollback을 구분한다.

근거: [시작 조건](https://docs.docker.com/compose/how-tos/startup-order/), [프로필](https://docs.docker.com/compose/how-tos/profiles/), [project 이름](https://docs.docker.com/compose/how-tos/project-name/), [Compose secret](https://docs.docker.com/compose/how-tos/use-secrets/), [서비스 명세](https://docs.docker.com/reference/compose-file/services/), [PostgreSQL 이미지](https://hub.docker.com/_/postgres).
