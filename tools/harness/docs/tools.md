# 설치·MCP·클라이언트 사용

모델 추천·별도 실행은 [선택 도구](execution.md)다. 일반 대화창의 UserPromptSubmit 자동 라우팅 훅은 등록하지 않는다.
라우터 훅의 활성화·신뢰 승인은 기본 작업의 준비 단계가 아니다.

## 기본 시작

Git과 Python 3.11 이상을 준비하고 레포 루트에서 실행한다.

```sh
python3 tools/harness/run.py setup
python3 tools/harness/run.py doctor
python3 tools/harness/run.py check --full
```

setup의 기본 동작은 Codex 프로젝트 구성을 점검하는 것이다. 스킬은 .agents/skills에서 직접 읽으며 복사하지 않는다.
개인 전역 설정·로그인 자료는 수정하지 않는다.
현재 Python 도구는 stdlib만 사용하므로 외부 패키지 설치가 필요 없다.
공식 Codex 클라이언트 설치·로그인은 별도 준비이며 이 명령이 구독·인증을 자동 설정하지 않는다.
Node.js는 선택적인 브라우저 MCP를 사용할 때 필요하다.
프로젝트 패키지 관리자 선택·고정 의존성 설치는 [setup-environment](../../../.agents/skills/setup-environment/SKILL.md)와 [환경 안내](environment.md)를 따른다.
기본 setup은 환경 선언도 읽어 보고하지만 의존성을 설치하지 않는다. install은 별도 명령이다.

Codex는 레포 루트에서 시작하고 AGENTS.md, .agents/skills, .codex/config.toml을 사용한다.
프로젝트 신뢰와 새 MCP 승인은 클라이언트의 기존 동작을 따른다. 이 레포는 승인 정책이나 모델 기본값을 덮어쓰지 않는다.
전역 설정이 함께 적용될 수 있으므로 /mcp에서 도구의 출처와 실제 로딩을 확인한다.
설정을 추가해도 이미 실행 중인 세션의 도구 목록이 즉시 바뀐다고 가정하지 않는다.
레포 훅 정의는 .codex/hooks.json에 있다. [생명주기 훅](hooks.md)과 [보류한 요청 라우팅 코드](execution.md#일반-codex-대화창의-자동-호출)를 구분한다. 훅을 사용할 때 /hooks에서 현재 정의를 검토한다. 파일 배치만으로 런타임 활성화를 완료했다고 하지 않는다.

## 기본 MCP

| 서버 | 연결 | 범위 |
| --- | --- | --- |
| openaiDeveloperDocs | https://developers.openai.com/mcp | OpenAI/Codex 공식 문서 |
| svelte | https://mcp.svelte.dev/mcp | 공식 Svelte 문서·정적 코드 분석 |

공개 HTTP 서버이므로 로컬 서버 패키지나 공유 API 키는 필요 없다. 네트워크는 필요하다.
일반 웹 검색은 클라이언트 기본 도구를 우선 사용한다. 문서 MCP를 범용 웹 검색으로 취급하지 않는다.
일반 Python 라이브러리 문서는 공식 웹 문서로 확인하며 Context7은 인증·제약을 확인한 뒤 필요할 때 추가한다.
파일·셸·Git 기능을 위해 중복 MCP를 설치하지 않는다.

```sh
python3 tools/harness/run.py mcp-check
```

이 명령은 .codex/config.toml의 활성 HTTP 서버를 읽어 initialize와 tools/list를 확인한다. 모델 호출·유료 API·제품 상태 변경을 수행하지 않는다.
실패는 unavailable로 보고하며, 통과해도 클라이언트 신뢰·도구 적용·실제 도구 호출까지 증명하지 않는다.
기존 라우터의 분류 프로세스는 계속 도구/MCP를 제한한다. 작업용 도구 설정을 분류기에 자동 노출하지 않는다.

## 선택적인 브라우저 MCP

```sh
python3 tools/harness/run.py setup --browser
```

tools/harness/browser의 잠금 파일로 @playwright/mcp 0.0.79와 의존성을 설치하고 Chromium을 내려받는다.
버전은 현재 사용 가능한 캐시에서 확인한 고정값이며 최신·최적 버전이라는 뜻은 아니다.
패키지·캐시·브라우저는 레포 안에 저장하며 설치 완료 후 .codex/config.toml에 playwright를 등록한다.
개인 Chrome 프로필·쿠키를 사용하지 않고 격리된 headless Chromium으로 실행한다.
클라이언트는 레포 루트에서 시작해야 상대 경로의 tools/harness/scripts/mcp-browser.mjs를 찾을 수 있다.
직접 브라우저를 제어하는 MCP와 반복 가능한 Playwright E2E 테스트는 별개의 검증 수단이다.
자동 E2E는 [E2E 스킬](../../../.agents/skills/e2e-testing/SKILL.md)의 설정 템플릿·프로젝트 로컬 @playwright/test·JUnit 실행 연결을 사용한다. MCP 설치만으로 자동 E2E가 준비되지는 않는다.
설치가 네트워크·OS 제약으로 실패하면 도구 등록/브라우저 실행을 완료했다고 보고하지 않는다.

## 확인 범위

macOS에서 Python 기능 테스트·문서/설정 점검을 확인한다. 다른 OS와 새 노트북 실측은 별도다.
외부 연결과 브라우저 설치 결과는 실행 당시 결과로 판단한다. 정적 설정 파일만으로 연결 성공을 주장하지 않는다.
2026-10-30 구성 당시에는 공개 서버의 DNS 조회가 제한되어 HTTP MCP 연결을 확인하지 못했다.
브라우저 패키지는 잠금 파일에 맞는 로컬 npm 캐시에서 설치해 MCP 통신과 도구 목록을 확인했다.
Chromium 다운로드와 실제 화면 검증은 미확인이다. 따라서 playwright 서버를 기본 설정에 등록하지 않았다.

공식 근거 (2026-10-30 확인):

- [Codex MCP](https://learn.chatgpt.com/docs/extend/mcp)
- [OpenAI 문서 MCP](https://developers.openai.com/learn/docs-mcp)
- [Svelte MCP](https://svelte.dev/docs/ai/mcp)
- [Playwright MCP](https://github.com/microsoft/playwright-mcp)
