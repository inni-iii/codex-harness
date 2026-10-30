---
name: python-backend
description: Implement or review Python services and backend behavior with appropriately sized packages, API boundaries, resource lifecycles and meaningful tests.
---

# Python 작업

1. Python 버전·pyproject·잠금 파일·진입점·기존 테스트를 확인한다. DB 선택은 PostgreSQL이며 FastAPI·ORM·driver 채택은 추측하지 않는다.
2. 입력에서 외부 출력까지 경로와 공유 자원·설정·권한 경계를 찾는다.
3. 업무 규칙과 I/O를 구분하고 현재 크기에 필요한 만큼만 구조를 만든다.
4. 정상 동작과 이번 변경으로 깨질 수 있는 경계를 검증한다. 실제 검사 명령을 워크플로에 등록한다.
5. 구체적인 예외와 원인을 보존하되 요청 본문·토큰·개인정보를 오류나 로그에 복사하지 않는다.

| 조건 | 읽을 자료 |
|---|---|
| 패키지·기능 배치·리팩터링 | [구조와 변경 단위](references/structure.md) |
| async·공유 클라이언트·앱 수명·트랜잭션 | [자원 관리](references/resources.md) |
| HTTP·OpenAPI·프론트 타입·권한 계약 | [API 계약](references/api-contracts.md) |
| pytest·API/DB·외부 호출 검사 | [테스트 경계](references/testing.md) |
| PostgreSQL schema·SQL·migration·쿼리 성능 | [Postgres 스킬](../postgres/SKILL.md) |
| 로그·요청 추적·재현되지 않는 실패 | [최소 관측](references/observability.md) |
| 외부 API·모델·스트림·배치 호출 | [외부 호출](references/external-calls.md) |

기능별 패키지를 Python 전체의 유일한 표준으로 주장하지 않는다. 작은 서비스에 빈 repository 계층을 만들지 않는다.
짧은 작업은 다음 구현과 검증을 쉽게 만드는 작은 정리를 우선한다.
라이브러리별 구문은 현재 공식 문서로 확인한다. 원격 서버의 검사·마이그레이션은 실행하지 않고 로컬에서 준비한다.
