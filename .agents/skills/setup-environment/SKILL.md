---
name: setup-environment
description: Inspect or prepare a repository on a new machine, reconcile declared package managers and lockfiles, and run authorized frozen local dependency installs.
---

# 환경과 프로젝트 의존성 준비

다른 노트북에서 하네스를 시작하거나 의존성·패키지 관리자·실행 환경을 연결할 때 읽는다.

1. AGENTS·프로젝트 개요·manifest·lockfile·실행 명령에서 필요한 환경과 사용자 제약을 확인한다.
2. environment inspect --path로 대상 프로젝트를 조사한다. Node/Python을 구분하고 선언·lockfile 충돌은 실제 프로젝트 결정을 확인해 정리한다.
3. setup/doctor의 정적 점검, 프로그램 존재, 로그인·서버 연결·앱 동작을 각각 구분한다.
4. 설치가 요청 범위에 있으면 environment install의 고정 lock 경로를 사용한다. 기본적으로 lifecycle/build script는 실행하지 않으며 필요한 경우 내용을 검토해 명시적으로 허용한다.
5. 관리자 버전·cwd·lock 상태·종료 결과를 확인하고 실제 앱 명령과 검증을 연결한다.

명령·지원 범위는 [환경 도구](../../../tools/harness/docs/environment.md)를 따른다.
개인 전역 선호로 저장소 관리자를 바꾸거나 global npm/pip 설정을 수정하지 않는다.
PostgreSQL·Codex 실행 프로그램 설치/로그인·원격 DB 준비는 의존성 동기화와 별개다.
시험 환경에서 브라우저가 금지돼 있으면 설치/실행을 포함하지 않는다. MCP·외부 서비스는 실제 요구에 필요한 경우에만 연결한다.

그래프로 절차·검증·재진입을 관리할 때는 [라우트 계약](routes.toml)에서 현재 작업을 고른다. `flow context <실행ID> --read`로 현재 절차와 허용된 다음 경로만 확인한다. 공통 실행 계약은 [스킬 흐름](../../../tools/harness/docs/skill-flows.md)을 따른다.
