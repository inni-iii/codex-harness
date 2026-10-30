# 실제 PostgreSQL 경계 검증

DB-backed 기능·migration·동시성·성능 변경에서 읽는다.

## 환경과 격리

프로젝트가 정한 PostgreSQL 버전·확장·driver·migration revision을 사용한다.
쓰기 전에 대상이 현재 작업용 로컬 테스트 DB인지 확인하고 각 세션/worker의 DB·schema·데이터를 격리한다.
운영 URL의 문자열 치환으로 테스트 DB를 고르지 않는다. localhost 프록시도 원격 서비스일 수 있으므로 호스트 이름만으로 로컬 격리를 증명하지 않는다.
외부 API 호출은 합성 데이터와 adapter로 통제하고 접속 비밀값을 로그에 남기지 않는다.

순수 업무 규칙은 단위 테스트로 빠르게 확인할 수 있다. PostgreSQL의 제약·SQL·잠금·JSONB·migration은 SQLite나 mock 통과만으로 검증했다고 하지 않는다.
앱이 요청 중 commit한다면 바깥 fixture의 rollback 하나로 정리된다고 가정하지 않는다. 프로젝트가 쓰는 savepoint·테스트 DB 재생성 등의 실제 정리 범위를 확인한다.

## 요구에 맞게 고를 검사

| 변경 | 확인할 실제 결과 |
|---|---|
| 저장·수정·삭제 | 재조회 결과·트랜잭션 실패 후 보존 상태·다른 사용자 자료 |
| UNIQUE/FK/CHECK/NOT NULL | 잘못된 입력 거부·기존 데이터 호환·앱의 오류 변환 |
| 중복·동시 갱신 | 서로 다른 연결/트랜잭션의 경쟁·허용 결과·중복 부작용 없음 |
| 페이지네이션 | 같은 정렬값·null·경계·누락/중복 정책 |
| RLS | 실제 앱 role·사용자별 SELECT/INSERT/UPDATE/DELETE·문맥 누수 |
| migration | 빈 DB와 이전 revision의 기존 데이터·필요한 복구 경로 |
| 성능 | 동일 조건 전후 결과·지연·쿼리 수·쓰기 영향 |

서로 순차 실행한 두 요청만으로 동시 경합을 시험했다고 하지 않는다. 재현이 필요하면 동기화 지점과 독립 연결을 사용한다.
DB 통과 후에도 API status·오류와 화면 소비자의 의미가 맞는지 필요한 연결 검사를 수행한다.
Python fixture·API 수명·JUnit 연결은 [백엔드 테스트](../../python-backend/references/testing.md), 사용자 흐름은 [E2E](../../e2e-testing/SKILL.md)를 따른다.

## 하네스에 등록할 것

실제 프로젝트의 DB 준비·migration·행동 검사 명령을 workflow의 checks에 등록하고 schema/migration 변경의 impacts를 앱·API 검사와 연결한다.
대상 버전·revision·합성 데이터·명령·보고서를 남긴다. 선택한 테스트가 0개·전체 skip·DB 미접속이면 실제 DB 검증은 미확인이다.
새 스킬과 문서 링크의 통과는 DB 서버 설치·스키마 적용·서비스 동작 확인의 증거가 아니다.
