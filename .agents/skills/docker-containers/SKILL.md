---
name: docker-containers
description: "Design, configure, inspect or diagnose Dockerfiles, Compose stacks and container environments for a target project, including images, networking, volumes, secrets, readiness and verification. Use for Docker/container infrastructure work; do not containerize the harness or force static Svelte deployment by default."
---

# 프로젝트의 Docker 컨테이너 구성

다른 프로젝트의 Dockerfile·Compose·개발/검사/운영 실행 환경을 설계·구성·진단할 때 사용한다. 스킬을 설치한 하네스 자체를 컨테이너화하라는 뜻이 아니다. 먼저 **어느 프로젝트의 무엇을 바꿀지** 확인하고 그 프로젝트의 파일을 다룬다.

## 작업과 경계를 고른다

| 요청 | 라우트 | 결과와 실행 경계 |
|---|---|---|
| 현재 Docker/환경/구성을 알아봐 | inspect | manifest·이미지·Compose·로컬 endpoint를 읽고 현재/누락/미검증을 보고 |
| 컨테이너 구조나 스펙을 설계해 | design | topology·이미지·네트워크·저장·복구·검사 계약. 파일 생성/기동은 요청 범위에서 판단 |
| Dockerfile/Compose를 만들거나 고쳐 | configure | 현재 설계/정렬에서 대상 파일을 작성하고 실제 관련 검증·문서를 연결 |
| 빌드/기동/통신이 왜 실패하지 | diagnose | 로그·상태·원문으로 원인을 좁힌다. 수정/재시작이 필요하면 허용 범위에서 configure로 연결 |

라우트는 [routes.toml](routes.toml)에 있다. 기록을 만드는 작업은 현재 task와 flow를 연결하고 현재 라우트의 원문을 읽는다. 읽기/설계 요청을 build/up/설치·배포 요청으로 확대하지 않는다. 기존에 맡긴 로컬 구성/수정/검증은 단계마다 재승인받지 않고 수행한다. 결과를 바꾸는 미결정만 묻는다.

## 수행 순서

1. 대상 레포의 지침·개요·실행 명령·manifest/lock·기존 Dockerfile/Compose/ignore/entrypoint를 읽는다. 대상 환경(dev/test/prod), OS/CPU/GPU, 현재 데이터·비밀·다른 실행의 소유권, 정상/오류/복구 수용 조건을 정한다. 기존 버전·패키지 관리자·프레임워크를 개인 선호로 바꾸지 않는다.
2. 실제 프로세스와 외부 의존성을 그린다. Svelte 프론트·Python API·PostgreSQL은 한 사례다. 프론트의 정적 배포를 강제하지 않는다. SvelteKit 프로젝트의 일반 서버형 구성에는 adapter-node를 검토하고 SSR/CSR/prerender는 화면 요구로 정한다. SvelteKit·Node SSR·FastAPI·ORM·Redis·검색 DB를 모든 프로젝트의 필수로 만들지 않는다.
3. [이미지 구성](references/images.md)으로 build context·ignore·lock·빌드/실행 단계·플랫폼·사용자·비밀·종료 신호를 맞춘다. build args/런타임 설정과 브라우저 공개 설정을 구분한다. Dockerfile 경로가 있어도 COPY 원본/ignore/실행 의존성까지 확인한다.
4. [Compose와 실행](references/compose.md)으로 환경별 파일·서비스 DNS·진입 경로·준비 확인·migration·권한·volume·자원·로그·복구를 연결한다. 포트·프로젝트·볼륨은 실행/worktree별로 격리한다. 외부 DB/스토리지나 기존 systemd timer 역할을 누락하지 않는다.
5. [검증과 진단](references/verification.md)에 따라 정적 검사→허용된 build/start→실제 요청/저장/재조회→실패·재시작·격리→자기 자원 정리를 필요한 범위에서 수행한다. config 통과와 앱 동작을 구분하고 E2E는 의미 있는 사용자 흐름이 완성될 때 관련 스킬로 검증한다.
6. 대상 프로젝트의 인프라 문서와 workflow 검사 명령에 버전·명령/cwd·소스 상태·정상/거부/실패·남은 조건을 남긴다. 전체 Git diff를 점검하고 기존 데이터/서비스를 건드리지 않았는지 확인한다. 필요하면 [명세 유지](../docs-maintenance/references/specifications.md)로 현재 설계와 동기화한다.

## 필요한 자료와 기존 스킬

- 프로젝트 계약은 [인프라 양식](assets/infrastructure.md)에 필요한 항목만 작성한다. [로컬 Compose 예제](assets/compose.local.example.yaml)는 이미지·앱 설정·버전·health 계약을 채워 사용하는 출발점이다. 실제 앱/운영 설정이나 검증된 배포물이 아니다.
- 패키지 관리자·고정 의존성은 [setup-environment](../setup-environment/SKILL.md), Python 프로세스/외부 호출은 [python-backend](../python-backend/SKILL.md), 프론트 서버/공개 설정/요청 흐름은 [svelte-frontend](../svelte-frontend/SKILL.md)를 따른다.
- schema·migration·트랜잭션·백업 복원은 [postgres](../postgres/SKILL.md), 신뢰 경계·비밀·의존성·Docker socket/권한은 [security-review](../security-review/SKILL.md), 브라우저 흐름은 [e2e-testing](../e2e-testing/SKILL.md), 완료/회귀 판단은 [verify-work](../verify-work/SKILL.md)가 정본이다.

## 항상 유지할 경계

SSH/SCP/SFTP/rsync 등으로 접근하는 원격 서버는 읽기 전용이다. 로컬 docker CLI라도 원격 endpoint를 가리키면 로컬 구성 권한을 적용하지 않는다. 원격 수정·build·기동·exec·캐시/로그 생성·migration은 하지 않는다.

비밀값·개인 인증/세션·호스트 .venv/node_modules를 이미지에 복사하지 않는다. privileged·host network·Docker socket mount를 기본 해결책으로 추가하지 않는다. 로그/inspect/config의 전체 출력으로 환경 변수나 비밀을 노출하지 않는다. 범위를 지정한 조회와 합성 데이터를 사용한다.

기존 컨테이너/볼륨을 무작정 재사용·교체하지 않고 global prune 또는 전체 자원 삭제를 정리 절차로 쓰지 않는다. 기존 데이터 volume을 지우는 down -v를 기본 실행하지 않는다. build/pull/up은 설치·다운로드·상태 변경이며 config/ps/info와 구분한다. 수행하지 못한 build/run/E2E·복원·성능은 미확인으로 남긴다.

이 스킬은 명령 자동 실행기나 보안 sandbox가 아니다. 로컬 권한·대상 프로젝트의 실제 계약과 실행 결과를 확인하는 절차다.
