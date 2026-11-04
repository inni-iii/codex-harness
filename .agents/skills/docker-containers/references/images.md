# 이미지와 Dockerfile

이미지를 작성/수정하거나 build 실패·과대 이미지·플랫폼 문제를 조사할 때 읽는다. 실제 프로젝트의 언어/프레임워크/lock과 현재 공식 문서를 기준으로 한다.

## 먼저 확인한다

1. Compose/build 명령의 기준 디렉터리 → context → Dockerfile → COPY/ADD 원본 → ignore → 실행 산출물 순으로 경로를 계산한다. 원본 부재와 ignore 제외, 다운로드 실패와 문법 오류를 구분한다.
2. Node/Python 버전·OS/libc·native wheel/module·런타임 라이브러리·브라우저/폰트·GPU가 필요한지 확인한다. Alpine을 작다는 이유만으로 선택하지 않는다.
3. 배포 대상 아키텍처와 로컬 아키텍처를 확인한다. arm64/amd64 manifest·native 의존성·선택한 이미지의 지원을 확인하고 강제 emulation을 무조건 해법으로 쓰지 않는다. CUDA/NVIDIA worker를 Mac의 일반 컨테이너 GPU 실행으로 검증했다고 하지 않는다.

## 빌드 계약

- 신뢰할 수 있는 base와 검토한 버전/태그를 선택하고 필요하면 digest로 묶는다. 태그 고정도 영구 불변을 뜻하지 않으며 업데이트·재검증 경로를 남긴다. 스킬에 특정 버전을 전역 기본으로 박지 않는다.
- manifest/lock을 먼저 복사하고 선언한 관리자의 고정 설치를 수행해 캐시를 분리한다. npm/pnpm/uv/pip 등은 프로젝트에 맞춘다. lock을 이미지 안에서 자동 갱신하거나 관리자를 바꿔 통과시키지 않는다.
- 빌드 도구가 필요한 단계와 최종 실행 단계를 구분한다. runtime에는 실제 필요한 산출물/라이브러리만 복사한다. 다단계가 의미 없는 작은 런타임까지 형식적으로 복잡하게 만들지 않는다.
- `.dockerignore`는 **context root** 기준이다. Dockerfile 전용 ignore가 있으면 우선 규칙도 확인한다. Git 제외 여부는 build 제외 여부가 아니다. `.env` 계열·키/인증·개인 세션·Git·호스트 native 의존성과 불필요 캐시를 실제 COPY 경로에서 제외한다. 디렉터리 전체 COPY에는 현재 포함되는 파일을 대조한다.
- private registry/package에 build 비밀이 필요하면 secret mount 등 현재 빌더의 지원 방식으로 전달한다. ARG/ENV나 COPY 후 삭제로 비밀을 이미지에 숨기려 하지 않는다. 런타임 비밀은 빌드와 분리한다.

## 실행 계약

가능한 경우 전용 일반 사용자를 사용하고 필요한 디렉터리만 쓰게 한다. DB 공식 이미지의 초기 사용자 전환 등 필요한 동작은 실제 계약을 읽고 별도로 처리한다. 임의 user/cap_drop로 entrypoint를 깨뜨리지 않는다.

실행 명령은 최종 이미지에 존재하는 프로그램·산출물·환경을 사용한다. JSON CMD/ENTRYPOINT와 wrapper의 exec/종료 코드를 확인하고, Compose command가 기존 ENTRYPOINT를 우회하는지 추측하지 않는다. init와 종료 유예는 장기 실행/worker의 수명에 맞춰 정한다. 컨테이너 init가 업무 task의 중복/재처리를 해결하는 것은 아니다.

healthcheck에 curl/wget/Node/Python을 쓰면 **최종 runtime**에 실제 존재하는지 확인한다. 단순 프로세스 실행·TCP 포트 열림·live·ready·업무 성공을 구분한다. 확인하지 못한 endpoint를 예제에서 복사하지 않는다.

SvelteKit을 선택했다면 adapter-node의 build 산출물과 Node 실행을 검토할 수 있다. static/SSR/CSR/prerender는 프로젝트·화면 요구로 정하며 Svelte 전체를 static이나 SvelteKit으로 동일시하지 않는다. npm lock 예제를 pnpm 프로젝트에 그대로 복사하지 않는다. Python은 선택한 프레임워크·패키지와 실제 app entrypoint, worker·DB pool 예산을 확인한다.

## build 검증과 보고

허용된 로컬 격리 환경에서만 실제 build를 수행한다. 설치/네트워크·base image 다운로드·build script를 먼저 검토하고 시간/디스크/출력 예산을 정한다. 플랫폼·명령/cwd·컨텍스트·lock·이미지 ID/digest·종료 코드와 실패 단계를 남긴다. 첫 build 검증을 캐시 hit/기존 이미지 실행으로 대체하지 않는다.

새 이미지에서 runtime import/실행·일반 사용자/쓰기 경로·health·종료를 실제 확인한다. 비밀 제외 검사는 합성 표식 파일과 대상 경로/레이어 계약으로 검증하며 실제 비밀을 출력/시험하지 않는다. static 검사만 했다면 build/run은 미확인이다.

근거: [빌드 원칙](https://docs.docker.com/build/building/best-practices/), [context/ignore](https://docs.docker.com/build/concepts/context/), [build secrets](https://docs.docker.com/build/building/secrets/), [플랫폼](https://docs.docker.com/build/building/multi-platform/), [SvelteKit Node](https://svelte.dev/docs/kit/adapter-node). 설정 구문과 위치는 선택한 버전 문서를 따른다.
