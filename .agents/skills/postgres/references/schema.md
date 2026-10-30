# 스키마·권한·트랜잭션

테이블·데이터 계약·쿼리 입력·저장 경계를 정하거나 바꿀 때 읽는다.

## 요구를 제약으로 연결하기

| 요구 | 확인할 설계와 동작 |
|---|---|
| 같은 자원을 중복 생성하면 안 됨 | 업무 키의 UNIQUE, 동시 충돌 처리, 멱등 요청 의미 |
| 없는 부모·잘못된 상태를 저장하면 안 됨 | FK·NOT NULL·CHECK, 삭제 정책과 기존 데이터 |
| 다른 사용자/조직의 자료에 접근하면 안 됨 | 조회·수정·삭제의 실제 권한 조건, 사용하는 DB role |
| 여러 변경이 함께 성공해야 함 | 트랜잭션 소유자, 실패 rollback, 외부 부작용 경계 |
| 순서가 안정적인 목록 | 정렬 기준·동률 해소 키·null·cursor 계약 |

사전 SELECT로 중복이 없음을 확인하는 것만으로 동시 INSERT를 막았다고 하지 않는다.
충돌은 DB 제약으로 구분하고, 이미 실패한 트랜잭션을 rollback/savepoint 처리 없이 계속 사용하지 않는다.
재시도가 필요하면 재시도 가능한 오류와 전체 업무 단위를 정하고 외부 결제·이메일이 중복되지 않는지 확인한다.

## 자료형과 조회

- ID는 기존 계약·생성 주체·분산 요구에 따라 bigint 또는 uuid 등을 고른다. 임의로 UUID를 금지하거나 새 서버 기능을 가정하지 않는다.
- 실제 시각은 보통 timestamptz를 검토하고, 날짜·현지 시각 요구와 구분한다. timestamptz가 원래 지역 이름을 보존한다고 가정하지 않는다.
- 금액·정밀 소수는 단위·정밀도·반올림을 합의한다. 특정 numeric 자릿수를 전 프로젝트에 고정하지 않는다.
- JSONB는 가변 문서에 유용하지만 핵심 관계·제약을 전부 숨기는 대체재로 쓰지 않는다. 실제 연산자와 조회 패턴에 맞춰 인덱스를 고른다.
- 값은 드라이버/ORM의 바인딩을 사용한다. 동적 테이블명·정렬 컬럼은 값 파라미터와 달리 허용 목록이나 식별자 API로 처리한다.

## 세션과 권한

연결 풀은 앱/worker 수명, 세션·트랜잭션은 작업 단위로 소유한다. 동시 task가 같은 가변 session을 공유하지 않는다.
commit 주체를 정하고 장시간 네트워크 대기 동안 DB 트랜잭션을 열어 두는지 확인한다. Python 수명은 [자원 관리](../../python-backend/references/resources.md)를 따른다.

앱의 owner_id 조건과 DB의 Row-Level Security는 서로 다른 방어다.
RLS를 채택하면 실제 앱 role로 SELECT/INSERT/UPDATE/DELETE를 검사한다. 소유자·superuser·BYPASSRLS의 우회를 고려하고 USING과 WITH CHECK를 구분한다.
풀 연결에 사용자 문맥을 설정한다면 요청 종료 뒤 다른 사용자에게 남지 않게 한다. 모든 프로젝트에 RLS를 강제하지 않는다.
인증·자원 권한 변경은 [보안 스킬](../../security-review/SKILL.md)에서 실제 거부와 금지된 부작용도 확인한다.

공식 기준: [제약](https://www.postgresql.org/docs/current/ddl-constraints.html), [트랜잭션 격리](https://www.postgresql.org/docs/current/transaction-iso.html), [RLS](https://www.postgresql.org/docs/current/ddl-rowsecurity.html). 사용하는 서버 버전의 문서를 확인한다.
