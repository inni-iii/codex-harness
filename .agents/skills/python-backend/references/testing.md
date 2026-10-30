# Python 테스트 경계

pytest·API·DB·외부 호출 검사를 설계할 때 읽는다.

## 무엇을 실제로 확인할지

- 업무 함수: 입력·경계·오류·불변 조건을 표나 parametrize로 명확히 한다.
- API: 실제 라우팅·검증·인증·응답·오류 변환을 통과시킨다.
- 외부 adapter: 합의된 요청·응답·실패·timeout을 확인한다. 업무 함수 전체를 mock하지 않는다.
- DB: 필요한 엔진의 제약·트랜잭션·조회 동작을 확인한다. SQLite 통과를 다른 DB 동작 증명으로 삼지 않는다.
- 버그 수정: 가능하면 기존 증상을 실패하는 회귀 검사로 남기고 수정 후 통과를 확인한다.

상태·임시 파일·환경을 fixture로 격리하고, 정리는 finally/context manager로 보장한다.
patch는 정의된 위치만 보지 말고 실제 조회되는 모듈에서 적용한다. async 호출은 await 여부도 검증한다.
테스트 수를 늘리기 위한 사소한 wrapper·서드파티 내부 구현 검사는 추가하지 않는다.
커버리지 숫자 하나를 임의의 전 프로젝트 완료 기준으로 고정하지 않는다.

## FastAPI를 선택한 경우

동기 TestClient라면 context manager로 시작·종료 이벤트를 실행한다.
AsyncClient+ASGITransport만 쓰면 앱 lifespan은 실행되지 않는다. 이는 [공식 async 테스트 안내](https://fastapi.tiangolo.com/advanced/async-tests/)에 명시되어 있다.
실제 앱 수명을 검증하려면 프로젝트가 사용하는 lifespan manager를 연결하거나 lifespan을 실행하는 별도 검사를 둔다.
수명 실행을 생략한 단위 검사라면 그 제한을 기록한다.

dependency_overrides는 테스트별 앱을 사용하거나 finally에서 원래 값을 복원한다.
공유 production 앱을 가져와 덮어쓴 뒤 다음 테스트에 상태를 남기지 않는다.
별도 테스트 설정을 명시하고 DB 대상을 검증한다. 운영 URL의 이름을 replace해서 테스트 DB를 선택하지 않는다.
요청 안에서 commit한 데이터를 단순 session.rollback만으로 되돌릴 수 있다고 가정하지 않는다.
프로젝트의 실제 transaction/savepoint 격리 방식을 검증한다.

## 실행 결과를 하네스에 연결

unittest는 test_summary=unittest, pytest는 test_summary=junit과 새 보고서 경로를 사용한다.
pytest의 [JUnit 출력](https://docs.pytest.org/en/stable/how-to/output.html)은 --junitxml로 설정할 수 있다.

```toml
[[checks]]
id = "backend-tests"
command = ["uv", "run", "pytest", "tests", "--junitxml={report}"]
cwd = "backend"
paths = ["backend/**"]
test_summary = "junit"
cacheable = false
timeout = 120
```

위 명령은 backend와 uv/pytest가 실제로 준비된 프로젝트에서만 등록한다. 현재 하네스에 설치됐다는 뜻이 아니다.
하네스는 {report}를 실행별 새 절대경로로 바꾼다. 0개·전체 skip·없는/잘못된 보고서를 통과로 인정하지 않는다.
외부 DB·시간·네트워크 상태에 따라 바뀌는 검사는 cacheable=false를 유지한다.
