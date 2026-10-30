# 쿼리와 인덱스의 성능 근거

느린 조회·쓰기·잠금·풀 대기를 바꿀 때 읽는다.

## 먼저 병목을 구분하기

쿼리 횟수/N+1, DB 실행, 반환량·직렬화, 연결 풀 대기, 잠금, 외부 호출 중 어디서 기다리는지 확인한다.
서버 버전·데이터 규모/분포·파라미터·동시성·warm/cold 조건과 결과의 의미를 기준선에 남긴다.
측정 없이 work_mem·풀 크기·서버 전역 설정을 올리지 않는다. 프로세스/worker별 합산 연결 수도 고려한다.

## 실행 계획을 읽기

EXPLAIN은 추정 계획이고 EXPLAIN ANALYZE는 쿼리를 실제 실행한다.
ANALYZE는 허용된 로컬 테스트 DB에서만 사용한다. SELECT도 함수·잠금·외부 효과를 가질 수 있고 rollback이 모든 부작용을 되돌리지는 않는다.
실제 쓰기 쿼리를 분석하기 전 실행·복구 범위를 확인한다. 원격에서는 이 스킬을 근거로 시험 실행하지 않는다.

계획에서 추정/실제 행 수, loops, 필터로 제거된 행, buffers, 정렬·디스크 유출, join과 반환량을 함께 본다.
Seq Scan이나 Nested Loop만 보고 결함으로 판정하지 않는다. 작은 테이블·넓은 결과에서는 합리적일 수 있다.
통계가 오래됐다는 가정과 실제 관측을 구분한다. ANALYZE·VACUUM도 상태를 바꾸는 관리 작업이다.

## 인덱스와 쿼리 후보

| 상황 | 검토할 후보와 비용 |
|---|---|
| 동등·범위·정렬 조회 | B-tree/복합 키. 실제 WHERE·ORDER BY·선택도·버전으로 순서를 판단 |
| 일부 상태만 자주 조회 | 부분 인덱스. 쿼리 조건이 predicate를 충족하는지 확인 |
| JSONB·배열·전문 검색 | 연산자에 맞는 GIN/opclass. 모든 JSONB 조회가 같은 인덱스를 쓰지는 않음 |
| 정렬된 대규모 범위 자료 | BRIN 등 후보를 실제 분포·조회 범위와 비교 |
| 깊은 페이지 | 안정된 복합 정렬과 keyset cursor. 동률·null·동시 변경 의미를 확인 |

인덱스는 저장 공간·쓰기·vacuum·생성 비용도 늘린다. PK/UNIQUE의 기존 인덱스를 확인하고 FK 인덱스 필요성은 실제 접근/삭제 패턴으로 판단한다.
INCLUDE가 항상 index-only scan을 보장하지 않고, 중복처럼 보이는 인덱스도 제약·정렬·연산자가 다를 수 있다.
부분 인덱스 predicate에 NOW()처럼 현재 시간에 의존하는 함수를 넣지 않는다. 인덱스 표현식과 predicate에는 immutable 제약이 있다.
EXISTS/IN, JOIN/서브쿼리, OR/UNION 중 하나가 항상 빠르다고 정하지 않는다. null·중복 등 의미 보존과 실제 계획을 확인한다.

## 변경 후 확인

같은 결과·데이터 조건에서 전후 시간·조회 수·계획·쓰기 영향·오류를 비교한다. 예상 개선을 실측으로 보고하지 않는다.
잠금·deadlock·serialization 오류는 단순 재시도로 덮지 말고 트랜잭션 순서·경계·재시도 단위를 확인한다.
공유 기록에는 민감한 리터럴·전체 원본 쿼리를 복사하지 않고 구조·합성 입력·필요한 지표만 남긴다.
서버 설정·복제·확장·pg_stat_statements 설치는 이 문서를 읽었다는 이유로 실행하지 않는다.

공식 기준: [EXPLAIN](https://www.postgresql.org/docs/current/using-explain.html), [인덱스](https://www.postgresql.org/docs/current/indexes.html), [인덱스 표현식·동시 생성](https://www.postgresql.org/docs/current/sql-createindex.html).
