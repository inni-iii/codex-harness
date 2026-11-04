# 조건부 문서 단계

```json
{
  "version": 1,
  "kind": "reasons-design",
  "profile": "behavioral",
  "requirements": [
    "R1",
    "R2",
    "R3"
  ],
  "operations": [
    {
      "id": "O1",
      "requirements": [
        "R1",
        "R2",
        "R3"
      ],
      "paths": [
        "tools/harness/harness/flow_documents.py",
        "tools/harness/harness/flow_catalog.py",
        "tools/harness/harness/skill_flows.py",
        "tools/harness/harness/flow_cli.py",
        "tools/harness/tests/test_conditional_docs.py",
        "tools/harness/docs/skill-flows.md",
        "tools/harness/docs/architecture.md",
        ".agents/skills/python-backend/routes.toml",
        ".agents/skills/svelte-frontend/routes.toml",
        ".agents/skills/postgres/routes.toml",
        ".agents/skills/docker-containers/routes.toml",
        ".agents/skills/verify-work/routes.toml",
        ".agents/skills/python-backend/SKILL.md",
        "docs/tasks/conditional-doc-flow/**"
      ],
      "depends_on": [],
      "verification": "동결 반례 RED/GREEN·문서 변화/기준 없음/필수 호출·재진입 보존·호출자/통합 검사"
    }
  ],
  "decisions": []
}
```

## Requirements
R1: 검증된 구현에서 문서 무변경이면 이유와 함께 문서 단계를 생략한다. R2: 실제 문서 변경/기준 없음/실패·필수 검사 누락은 생략하지 않는다. R3: Git 없이 내용 해시로 판단하고 이전 상태·재진입·CLI/현재 계약을 보존한다.

## Entities
등록 route의 finish_when=documents_unchanged가 선택 종료 조건이다. 해당 frame 진입 때 정본 문서의 경로→SHA를 보존한다. docs/tasks 수행 기록은 제외하고 docs/·tools/harness/docs 및 그 밖 Markdown/문서 양식을 비교한다.

## Approach
기존 finish=false와 문서 continuation은 유지한다. 검증·필수 호출을 통과하고 기준/현재 문서 해시가 같고 이유를 남긴 경우에만 finish를 허용한다. 관련 없는 변경을 의미로 자동 추정하거나 문서 수정 필요 여부를 자동 승인하지 않는다. 이전 frame은 기준이 없어 보수적으로 continuation을 유지한다.

## Structure
flow_documents는 문서 분류/스냅샷/차이를 담당한다. catalog의 명시 조건·flow frame/finish/status와 CLI reason에 연결한다. Python/Svelte/Postgres/Docker/repair 구현 경로에 적용하고 현재 안내를 동기화한다.

## Operations
### O1
실제 Git 없는 fixture에서 선언 문법만 준비한 기존 종료 gate의 무변경 실패를 동결한다. 변경 경로·메모·같은 내용·재시도/명시 restart·이전 frame·필수 검증과 실제 CLI를 확인한다.

## Norms
현재 사용자 승인2번만 수행한다. 구현/검증/완료 강도를 줄이지 않고 의미 판단은 에이전트가 이유로 기록한다. UI 변경 없어 E2E 비적용. 3·4번과 다른 세션 변경은 별도 소유로 유지한다.

## Safeguards
변경된 문서는 기존 문서 경로로 이어간다. 기준은 프레임에 보존하고 retry/restart에서 새 기준으로 덮어 미처리 변경을 숨기지 않는다. 원본/상태 무결성·검증·입력/권한·과거 이력을 유지한다. 기준을 모르면 지름길을 허용하지 않는다.
