---
name: postgres
description: Design or review PostgreSQL schemas, SQL, transactions, migrations and query performance, and verify behavior against an isolated local PostgreSQL database.
---

# PostgreSQL 작업

이 하네스의 DB 선택은 PostgreSQL이다. 서버 버전·드라이버·ORM·migration 도구·확장은 프로젝트에서 정한다.
Python 서비스 작업이면 [백엔드 스킬](../python-backend/SKILL.md)과 연결하되 SQL만 다루는 작업에도 적용한다.

1. 현재 요구·스키마·migration 이력·주요 쿼리·서버 버전과 실제 접속 대상을 확인한다. 접속 문자열의 비밀값은 출력하지 않는다.
2. 데이터의 불변 조건, 소유권, 중복·동시 요청·실패 시 의미를 정하고 DB 제약과 트랜잭션 경계에 연결한다.
3. 기존 데이터와 호출자의 호환성을 확인하고, 필요한 SQL·migration·애플리케이션 변경을 작은 단위로 준비한다.
4. 실제 PostgreSQL의 격리된 로컬 테스트 DB에서 관련 동작을 확인한다. 성능 변경은 동일 조건의 기준선과 비교한다.
5. 스키마 revision·데이터 조건·실행 명령·검사 결과·남은 잠금/복구 위험을 기록하고 프로젝트 workflow의 checks/impacts에 연결한다.

| 조건 | 읽을 자료 |
|---|---|
| 테이블·자료형·제약·권한·트랜잭션 | [스키마와 데이터 계약](references/schema.md) |
| 스키마 변경·데이터 변환·기존 데이터 호환 | [마이그레이션](references/migrations.md) |
| 느린 SQL·인덱스·조회량·연결 경합 | [쿼리 성능](references/performance.md) |
| 실제 DB·동시 요청·migration 검증 연결 | [DB 검증](references/testing.md) |

실제 DB 생성·삭제·변경은 접속 대상과 현재 권한이 확인된 로컬 테스트 환경에서만 수행한다.
SSH 등으로 접근하는 원격 서버에는 SQL 변경·migration·ANALYZE·VACUUM·확장 설치·시험 실행을 하지 않는다.
스킬 추가는 PostgreSQL 서버·ORM·pgvector·DB MCP 설치나 원격 접속을 의미하지 않는다.

그래프로 절차·검증·재진입을 관리할 때는 [라우트 계약](routes.toml)에서 현재 작업을 고른다. `flow context <실행ID> --read`로 현재 절차와 허용된 다음 경로만 확인한다. 공통 실행 계약은 [스킬 흐름](../../../tools/harness/docs/skill-flows.md)을 따른다.

코드/행동 변경 전에는 [설계와 정렬](../plan-project/references/reasons-canvas.md)의 현재 의도·변경 경계·선택 O를 확인한다. 이 구현 flow에는 현재 design/alignment artifact를 연결하며 기존 결정이 충분하면 새 승인 질문을 반복하지 않는다.
