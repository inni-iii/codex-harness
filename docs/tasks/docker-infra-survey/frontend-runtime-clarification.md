# 범용 컨테이너 구성 기준 보완

2026-11-04 사용자 정정: “svelte는 무조건 정적 구성을 할 필요는 없어. 그냥 일반적으로 통용되는 그런 구성으로 컨테이너로 구성하고 싶은거야.”

기존 [조사 보고서](report.md)의 저장소별 정적/Node 배포 사례는 관측 사실이다. 그 사례를 범용 하네스의 정적 배포 요구로 일반화하지 않는다. 기존 완료 보고서와 당시 검토 근거는 보존하고, 이후 인프라 설계에는 이 보완 기준을 적용한다.

## 사용자 의도와 권장 기본안

사용자가 원하는 것은 프론트·백엔드·DB가 독립적으로 실행되고 Docker Compose로 연결되는 재사용 가능한 서비스 구성이다. 정적 빌드를 선행 조건으로 두지 않는다.

```text
브라우저 → 진입 프록시
              ├─ /      → frontend 컨테이너
              └─ /api/  → backend 컨테이너 → PostgreSQL 컨테이너
```

| 역할 | 권장 기본안 | 구분할 것 |
|---|---|---|
| frontend | SvelteKit을 선택하는 프로젝트에서는 adapter-node로 빌드한 Node 서버 | SSR·CSR·prerender는 화면별 요구에 따라 사용. Node 서버 실행이 모든 화면의 SSR 강제를 뜻하지 않음 |
| backend | 프로젝트가 선택한 Python API 서버를 별도 이미지/컨테이너로 실행 | 업무 로직·DB 권한·migration은 해당 프로젝트 계약으로 관리 |
| database | PostgreSQL, 전용 영속 볼륨·준비 확인·백업/복구 계약 | DB 버전과 확장은 프로젝트에서 선택 |
| proxy | 운영 진입점과 TLS·경로 라우팅. 제품에 맞게 Nginx/Caddy 등 선택 | 로컬 개발에서는 필요에 따라 직접 포트 접근도 가능 |
| 선택 서비스 | 실제 비동기/캐시/파일/검색 요구가 있을 때 worker·Redis 등 추가 | 전체 부가 스택을 기본 기동하지 않음 |

Node 서버형 frontend는 이번 범용 구성의 **권장안**이다. 사용자의 정정을 “SvelteKit·Node·SSR을 모든 프로젝트에 의무화한다”는 결정으로 확대하지 않는다. 현재 AGENTS의 공통 Svelte/Python/PostgreSQL 경계와 프로젝트별 프레임워크 선택은 유지한다.

SvelteKit의 adapter-node는 독립 Node 서버를 생성한다. 렌더링 방식은 페이지/레이아웃별로 조정하고 혼합할 수 있다. [공식 Node 서버 문서](https://svelte.dev/docs/kit/adapter-node), [공식 페이지 옵션](https://svelte.dev/docs/kit/page-options). 설치·설정 위치는 실제로 선택한 SvelteKit 버전 문서를 따른다.

## 컨테이너 실행 계약

- 개발: frontend 개발 서버와 backend reload, 소스 mount를 명시적인 dev 구성으로 관리한다. 호스트 node_modules/.venv가 컨테이너 의존성을 덮지 않게 한다.
- 운영: frontend/backend 각각 빌드한 실행 이미지를 사용한다. 개발 서버·reload·소스 전체 mount를 사용하지 않는다.
- 네트워크: 외부 진입점과 내부 서비스 네트워크를 구분한다. 브라우저는 공개 경로를, 서버 간 호출은 Compose 서비스 DNS를 사용한다. DB는 기본 외부 포트 없이 내부 접근한다.
- Node frontend의 프록시 origin/header 신뢰 범위, 쿠키·세션 전달, 서버용 API 주소와 브라우저용 주소를 실제 앱에서 검증한다. Python API의 인증·자원 권한은 backend에서 확인한다.
- 기존 조사안의 환경별 Compose·이름/포트/볼륨 격리·secret 주입·healthy/migration 조건·일회성 검사 runner 원칙은 그대로 적용한다.

구현 시 수용 기준은 frontend Node 서버 기동, 브라우저 탐색/새로고침, frontend→backend 통신, API→DB 저장/재조회, 재기동 후 데이터 유지, 오류 경로와 실행별 자원 격리다. 이번 보완은 설계 문서이며 실제 이미지 빌드·컨테이너 기동·E2E는 수행하지 않았다.
