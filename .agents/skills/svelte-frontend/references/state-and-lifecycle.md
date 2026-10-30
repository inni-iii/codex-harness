# Svelte 상태와 수명

Svelte 5 runes, 요청 경합, 구독·타이머를 구현할 때 읽는다. 기존 버전에는 해당 문법을 그대로 적용하지 않는다.

## 상태를 어디에 둘지

| 상태 | 우선 검토할 위치 | 놓치기 쉬운 문제 |
|---|---|---|
| 한 컴포넌트의 편집·열림 | 컴포넌트 로컬 | props와 복제 상태의 불일치 |
| 현재 트리에서 공유 | 인스턴스별 context/factory | SSR 사용자 간 모듈 상태 공유 |
| URL에 남아야 할 필터 | 라우트/URL 상태 | 새로고침·뒤로가기와 불일치 |
| 서버 권한·계정 정보 | 요청/서버 세션 | 브라우저 값을 권한 근거로 신뢰 |
| 반복 조회 데이터 | 프로젝트의 명시적 캐시 | 사용자·키·무효화 경계 누락 |

SvelteKit 서버의 공유 가변 상태는 사용자 간 유출로 이어질 수 있다. [공식 상태 관리 안내](https://svelte.dev/docs/kit/state-management)를 확인한다.
SSR에서는 사용자별 객체를 요청/컴포넌트 트리마다 만들고 context로 전달한다.

## runes 판단

계산 가능한 값은 $derived로 표현한다. $effect로 같은 값을 다시 동기화하면 반복 실행·순서 의존이 생길 수 있다.
$state.raw는 불변 대량 데이터의 재할당에 적합할 수 있지만 내부 push로 갱신될 것이라 기대하지 않는다.
일반 Map/Date 같은 객체의 내부 변경이 원하는 반응성을 만드는지 확인한다.
props를 수정할 소유자가 누구인지 정한다. 양방향 바인딩은 의도한 공개 계약일 때만 사용한다.
효과의 의존성은 동기 실행에서 읽은 값이다. await 뒤에 처음 읽은 값이 자동 추적된다고 가정하지 않는다.
현재 runes의 정확한 동작은 [공식 $effect 문서](https://svelte.dev/docs/svelte/$effect)에서 버전에 맞게 확인한다.

## 비동기 검색 경합 예시

setTimeout만 취소하면 이미 시작한 fetch는 남는다.
요청 취소와 오래된 결과 무시를 함께 고려한다. 아래는 클라이언트 검색을 위한 부분 예제다.

```svelte
<script lang="ts">
  let query = $state('');
  let result = $state<unknown>(null);
  let state = $state<'idle' | 'loading' | 'ready' | 'error'>('idle');

  $effect(() => {
    const term = query.trim();
    const controller = new AbortController();
    let current = true;
    if (!term) {
      result = null;
      state = 'idle';
      return;
    }
    state = 'loading';
    const timer = setTimeout(async () => {
      try {
        const response = await fetch(
          `/api/search?q=${encodeURIComponent(term)}`,
          { signal: controller.signal }
        );
        if (!response.ok) throw new Error('search failed');
        const data: unknown = await response.json();
        // 실제 프로젝트에서는 계약에 맞게 data를 검증한다.
        if (current) {
          result = data;
          state = 'ready';
        }
      } catch {
        if (current && !controller.signal.aborted) state = 'error';
      }
    }, 250);
    return () => {
      current = false;
      clearTimeout(timer);
      controller.abort();
    };
  });
</script>
```

예제의 대기 시간과 endpoint는 프로젝트 선택이다. 이 참조 파일은 앱에서 실행되는 코드가 아니다.
실제로 적용하면 느린 이전 요청이 빠른 최신 요청 뒤에 끝나는 사례와 컴포넌트 해제를 검사한다.

## 구독·스트림

EventSource·WebSocket·타이머·DOM listener의 생성 위치와 해제 위치를 짝짓는다.
효과 재실행, 라우트 이동, 오류, 탭 종료에서 중복 구독·해제 후 상태 갱신이 없는지 확인한다.
ReadableStream의 start가 반환한 함수를 정리 콜백으로 가정하지 않는다. 사용하는 API의 cancel/abort 계약을 확인한다.
