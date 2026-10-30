# 자원 수명·비동기·트랜잭션

장기 실행 서비스의 HTTP/DB 클라이언트, 스트림, 백그라운드 작업을 바꿀 때 읽는다.

## 소유자부터 정하기

| 자원 | 보통의 소유 범위 | 확인할 실패 |
|---|---|---|
| 연결 풀·HTTP client | 앱/worker 수명 | 일부 시작 실패·종료 중 누수 |
| DB session·transaction | 요청/업무 단위 | 실패 rollback·동시 task 공유 |
| 스트림 response·파일 | 해당 처리 범위 | 취소·예외·조기 종료 |
| 사용자별 상태 | 요청/명시적 세션 범위 | 다른 사용자와 교차 오염 |
| 순수 설정·컴파일 regex | 변경 없는 공유 값 | 테스트별 덮어쓰기·숨은 I/O |

일회성 스크립트의 요청별 client와 장기 서버의 요청마다 새 연결 풀 생성은 비용이 다르다.
풀을 공유하더라도 DB session 같은 작업별 상태까지 공유하지 않는다.
async 함수 안의 동기 파일·네트워크·CPU 작업은 event loop를 막는지 확인하고 적절한 실행 경계로 옮긴다.
재시도는 연결 실패·응답 상태·비멱등 작업을 구분한다. 중복 생성이나 비용 중복을 일으키는 재시도를 기본 추가하지 않는다.

## FastAPI를 선택한 경우의 앱 수명 예시

다음은 소유권을 보여 주는 예시다. 패키지 버전과 프로젝트 설정에 맞춰 조정한다.

```python
from contextlib import AsyncExitStack, asynccontextmanager
import httpx
from fastapi import FastAPI

def create_app(api_timeout: float = 10.0) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with AsyncExitStack() as resources:
            client = await resources.enter_async_context(
                httpx.AsyncClient(timeout=api_timeout)
            )
            app.state.http_client = client
            # 다른 자원도 생성 직후 cleanup을 등록한다.
            yield

    return FastAPI(lifespan=lifespan)
```

명시적 수명은 [FastAPI lifespan 문서](https://fastapi.tiangolo.com/advanced/events/), 여러 자원의 정리는 [Python AsyncExitStack](https://docs.python.org/3/library/contextlib.html#contextlib.AsyncExitStack)을 확인한다.
추가 자원 생성이 실패해도 앞서 얻은 자원을 정리하도록 구성한다. yield 아래 정리 코드만 나열하고 예외 시 실행을 가정하지 않는다.
시작·정상 종료뿐 아니라 두 번째 자원 시작 실패·취소 때의 정리도 필요한 범위에서 검사한다.

## 트랜잭션과 외부 부작용

한 업무 단위에서 누가 commit하는지 한 곳에 정한다. 라우터와 service가 각각 commit해 부분 저장되는지 확인한다.
오류 시 rollback, 중복 요청, 유니크 제약 경합을 검토한다. 외부 결제/이메일과 DB commit을 하나의 트랜잭션이라고 가정하지 않는다.
동시에 실행되는 작업에 가변 session을 그대로 공유하지 않는다. ORM별 공식 동시성 지침을 확인한다.
SSE·WebSocket·백그라운드 작업은 클라이언트 종료·서버 종료·예외 때 구독·작업·연결이 정리되는지 확인한다.

토큰·전체 요청 본문·DB 연결 문자열은 로그에 남기지 않는다. 오류 종류·요청 식별자·정리 결과처럼 필요한 정보만 남긴다.
