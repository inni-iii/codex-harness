---
name: svelte-frontend
description: Implement or review Svelte components and frontend flows, including reactive state, API integration, UI contracts and browser verification.
---

# Svelte 작업

1. package.json·잠금 파일·기존 컴포넌트에서 Svelte 버전, 프레임워크, 검사 명령을 확인한다.
2. 기존 토큰·컴포넌트·디자인 기준을 찾는다. 미정인 브랜드는 [디자인 스킬](../design-first/SKILL.md)로 결정을 준비한다.
3. 사용자 동작, 상태 전이, API/오류 계약, 서버·클라이언트 경계를 확인한다.
4. 기존 구조에 맞게 구현하며 관련 정적·단위 검사를 수행한다. 의미 있는 사용자 기능 묶음이 완성되면 사전에 알린 범위의 관련 E2E와 필요한 화면 확인을 수행한다.
5. 불확실한 API·문법은 해당 버전 공식 문서나 사용 가능한 Svelte MCP로 확인한다.

| 조건 | 읽을 자료 |
|---|---|
| runes·공유 상태·비동기 검색·이벤트 구독 | [상태와 수명](references/state-and-lifecycle.md) |
| SvelteKit load·인증·form actions·SSR | [데이터와 폼](references/data-and-forms.md) |
| 공용 컴포넌트·접근성·화면 상태 | [UI 계약](references/ui-contracts.md) |
| Python API·오류·생성 타입 변경 | [API 계약](../python-backend/references/api-contracts.md) |
| 브라우저 경합·시각 비교 | [브라우저 검증](../verify-work/references/browser.md) |
| 폼·탐색·인증·API 연결·공통 UI 동작 변경 | [관련 E2E 작성·실행](../e2e-testing/SKILL.md) |

클라이언트 전용 앱에 SvelteKit 파일을 만들지 않는다. 작업과 무관한 legacy 컴포넌트 일괄 변환을 하지 않는다.
사용자별 서버 상태를 모듈 singleton에 넣지 않는다. 생성 타입은 런타임 응답·권한 검사를 대신하지 않는다.
미실행 브라우저 확인을 통과로 기록하지 않는다. 프로젝트의 실제 검사 스크립트를 사용한다.
