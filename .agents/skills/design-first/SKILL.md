---
name: design-first
description: Define or apply an agreed design system for frontend work, including design authority, semantic tokens, component contracts and visual evidence.
---

# 디자인 기준부터 연결하기

현재 하네스에 특정 브랜드·색상·서체를 확정하지 않는다. 사용자와 차근차근 정한다.

1. 현재 요청과 프로젝트 자료에서 승인 기준·기존 구현·탐색용 초안을 구분한다.
2. 기준이 있으면 실제 코드와 비교하고 필요한 컴포넌트·토큰부터 검색한다.
3. 기준이 없으면 [디자인 템플릿](assets/design-system.md)으로 핵심 화면·톤·토큰·필수 상태를 함께 정한다.
4. 합의된 토큰 → 필요한 공용 컴포넌트 → 기능 조합으로 구현한다.
5. 실제 렌더링에서 관련 상태·뷰포트·키보드·필요한 테마를 확인하고 기준과 근거를 연결한다.

| 조건 | 읽을 자료 |
|---|---|
| 토큰·컴포넌트 API·기준 충돌·공통 UI | [디자인 계약](references/contracts.md) |
| 스크린샷·상태별 시각 비교 | [화면과 접근성](../e2e-testing/references/visual.md) |
| Svelte 구현과 접근성 | [UI 계약](../svelte-frontend/references/ui-contracts.md) |

사소한 컴포넌트 추가마다 재승인을 강제하지 않는다. 현재 요청으로 승인된 범위에서 진행한다.
서로 충돌하는 승인 기준처럼 결과를 바꿀 미결정만 확인한다.
Figma·Storybook은 선택이다. 작은 프로젝트는 토큰 파일과 컴포넌트 데모로 시작하고, 사용하지 않는 라이브러리를 미리 만들지 않는다.

그래프로 절차·검증·재진입을 관리할 때는 [라우트 계약](routes.toml)에서 현재 작업을 고른다. `flow context <실행ID> --read`로 현재 절차와 허용된 다음 경로만 확인한다. 공통 실행 계약은 [스킬 흐름](../../../tools/harness/docs/skill-flows.md)을 따른다.
