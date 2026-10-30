# 재현 가능한 PostgreSQL 변경

스키마·인덱스·기존 데이터 변환을 준비할 때 읽는다. ORM·migration 도구는 기존 프로젝트 선택을 따른다.

## 변경 전에 확인할 것

- 현재 revision과 실제 스키마, 대상 버전·확장·앱의 기존 소비자.
- 기존 null·중복·잘못된 FK·데이터 규모와 변경 중 계속 들어오는 쓰기.
- 필요한 잠금·테이블 재작성·검증 스캔·트랜잭션 시간과 실패 후 복구 방법.

공유 환경에 이미 적용된 migration은 수정하지 않고 후속 변경을 만든다.
자동 생성 결과는 rename·데이터 변환·제약·인덱스가 의도대로인지 검토한다. 모델과 일치한다는 이유만으로 안전하다고 하지 않는다.

## 작은 변경과 호환 변경

새 빈 로컬 DB의 초기 테이블 생성에는 불필요한 다단계 절차를 강제하지 않는다.
기존 데이터와 이전 앱이 함께 동작해야 한다면 다음 경계를 정한다.

1. 새 필드/구조를 추가하고 구버전도 사용할 수 있게 한다.
2. 필요한 이중 쓰기 또는 변경 추적을 연결해 backfill 중 새로 바뀌는 데이터도 놓치지 않는다.
3. 재개 가능한 기준 키·진행 상태·검증으로 기존 데이터를 변환한다.
4. 새 읽기로 전환하고 일관성과 구소비자 종료를 확인한 뒤 이전 구조를 제거한다.

backfill을 SQL 반복문으로 나눴다고 트랜잭션도 나뉘는 것은 아니다. 실제 commit 경계를 확인한다.
원본 값이 null이면 변환 후에도 null인 행을 계속 고르는 무한 반복이 생기지 않도록 완료 조건을 정한다.
데이터 복구가 불가능한 변경을 형식적인 downgrade로 되돌릴 수 있다고 하지 않는다. forward fix·백업 복원·손실 범위를 구분한다.

## PostgreSQL에서 잘못 가정하기 쉬운 것

- nullable 컬럼 추가도 잠금이 필요하다. 테이블 재작성 여부와 잠금 획득·대기는 서로 다르다.
- 기본값·NOT NULL의 비용은 표현식·기존 데이터·버전에 따라 다르다. 모든 경우를 무잠금/즉시 또는 전체 재작성으로 단정하지 않는다.
- CREATE INDEX CONCURRENTLY는 동시 쓰기를 허용하지만 무잠금·무비용이 아니며 트랜잭션 블록 안에서 실행할 수 없다. 실패 시 invalid 인덱스 상태도 확인한다.
- 모든 인덱스 생성에 CONCURRENTLY를 강제하지 않는다. 새 빈 테이블과 쓰기 중인 큰 테이블의 조건이 다르다.
- Alembic을 선택했다면 해당 버전의 autocommit_block 등 트랜잭션 API를 확인한다. 임의 COMMIT 삽입으로 주변 migration의 원자성을 깨지 않는다.

## 로컬 검증과 기록

격리된 PostgreSQL에서 빈 DB→최신 revision, 이전 revision+합성 기존 데이터→최신 revision을 각각 확인한다.
데이터 보존·제약·현재 앱 동작을 확인하고 downgrade를 지원한다면 데이터 손실 조건까지 검사한다.
SQL 검토·offline 생성만 수행했다면 실제 migration 검증은 미실행으로 남긴다.
원격 적용 명령은 수행하지 않는다. 필요한 수정 파일과 적용·복구 조건을 로컬에서 준비한다.

공식 기준: [ALTER TABLE 잠금과 동작](https://www.postgresql.org/docs/current/sql-altertable.html), [CREATE INDEX](https://www.postgresql.org/docs/current/sql-createindex.html), [Alembic 트랜잭션 블록](https://alembic.sqlalchemy.org/en/latest/api/runtime.html#alembic.runtime.migration.MigrationContext.autocommit_block).
