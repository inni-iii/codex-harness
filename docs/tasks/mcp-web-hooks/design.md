# MCP 호출 훅과 내장 웹검색 검증

```json
{
  "version": 1,
  "kind": "reasons-design",
  "profile": "behavioral",
  "requirements": [
    "R1",
    "R2",
    "R3",
    "R4"
  ],
  "operations": [
    {
      "id": "O1",
      "requirements": [
        "R1",
        "R2",
        "R3",
        "R4"
      ],
      "paths": [
        ".codex/hooks.json",
        "tools/harness/harness/lifecycle_hooks.py",
        "tools/harness/tests/test_lifecycle_hooks.py",
        "tools/harness/docs/hooks.md",
        "tools/harness/docs/architecture.md",
        ".agents/skills/security-review/references/harness.md",
        ".agents/skills/research/SKILL.md",
        ".agents/skills/research/references/web-search.md",
        ".agents/context.toml",
        "AGENTS.md",
        "docs/tasks/index.md",
        "docs/tasks/mcp-web-hooks/**"
      ],
      "depends_on": [],
      "verification": "실제 stdin과 MCP 오류/비신뢰 입력·변경 감지·기존 셸 회귀, context 선택과 내장 웹검색 전후 시나리오, 등록 검사 전체"
    }
  ],
  "decisions": [
    {
      "id": "D1",
      "status": "resolved",
      "operations": [
        "O1"
      ],
      "reason": "현재 사용자가 직전 제안의 적용을 요청했다. 이미 연결된 MCP를 인식하는 훅과 내장 웹검색의 명시적 절차만 추가한다."
    }
  ]
}
```

## Requirements
R1: 연결된 MCP 이름을 Pre/Post에서 인식하고 셸 파서와 분리한다. R2: 호출 전 목적·권한·민감 인자, 호출 후 오류/응답 검토를 짧게 안내하며 원문을 복사하지 않는다. R3: MCP가 바꾼 watched 소스도 기존 정적 검사로 확인한다. R4: 내장 웹검색은 자동 이벤트 대신 명시적인 검색 전후 절차와 context 연결을 제공한다.

## Entities
입력은 Codex 이벤트의 session_id·tool_name·tool_input·tool_response다. MCP 이름은 mcp__서버__도구 형식만 인식한다. 원문 입력/응답은 일시적으로 읽고 저장하지 않는다. 기존 세션 상태는 task 바인딩·watched 해시·정적 결과만 소유한다. 웹 원문과 인용의 의미는 에이전트가 검토한다.

## Approach
서버별 도구 목록을 하드코딩하지 않고 MCP 이름 패턴을 matcher와 handler에 같이 적용한다. Pre는 고정된 권한/인자 안내만, Post는 명시적인 isError 또는 누락/오류 상태 형식 확인 안내와 비신뢰 응답 검토 안내를 반환한다. 자동 허용·거부·인자 변경·재시도는 추가하지 않는다. Post의 기존 watched 검사는 MCP에도 적용하되 새 변경이 없으면 재사용한다. 모든 도구를 셸 입력으로 보내는 대안은 도구별 인자가 달라 제외한다. 내장 WebSearch를 matcher에 추가하는 대안은 호스트가 이벤트를 내지 않아 제외한다.

## Structure
기존 lifecycle_hooks.py에 작은 MCP 이름/안내 helper를 두고 별도 서비스나 공통 추상화를 만들지 않는다. hooks.json의 두 도구 matcher와 테스트를 동기화한다. 검색 절차의 정본은 research/references/web-search.md에 두고 research 본문·AGENTS·context와 hooks 문서는 적용 조건·경계만 연결한다.

## Operations
### O1
위 paths의 코드·설정·관련 지침·검사를 함께 변경한다. MCP는 셸 가드를 호출하지 않고 Post 정적 점검을 유지한다. 잠금이 바빠도 비신뢰 응답 검토 안내는 반환하며 세션 상태 충돌을 피한다. 정상/오류/누락/악성 문자열과 실제 stdin을 검사한다. 내장 검색은 민감 질의·빈 결과·상충 자료의 실패 조건을 명시하고 실제 공식 문서 원문과 인용을 대조한다.

## Norms
새 MCP 서버/계정/플러그인·모델 호출·외부 업로드를 추가하지 않는다. 사용자와 도구 응답의 실행 권한을 분리한다. 기존 SSH 읽기 전용 규칙과 새 훅 정의의 호스트 신뢰 검토를 유지한다. 검색 요약을 원문 확인으로 대신하지 않는다.

## Safeguards
원문 명령·응답·도구 이름을 메시지에 끼워 넣지 않고 고정 안내만 반환한다. isError=true는 성공 근거로 쓰지 않도록 알리며 프롬프트 문자열 필터를 완전한 방어로 표현하지 않는다. 기존 stdin2MiB·깊이 제한을 유지하고 과대 입력은 미검증/콜백 실패로 남긴다. 훅 안내·정적 검사·문서상 절차가 실제 의미 검증이나 모든 도구 차단을 보증하지 않는다. 새 정의는 Codex에서 다시 검토·신뢰가 필요하며 이를 자동 설정하지 않는다.
