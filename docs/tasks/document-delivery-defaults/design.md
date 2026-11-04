# 요구 문서 기반 수행의 기본 절차

```json
{
  "version": 1,
  "kind": "reasons-design",
  "profile": "behavioral",
  "requirements": [
    "R1",
    "R2"
  ],
  "operations": [
    {
      "id": "O1",
      "requirements": [
        "R1",
        "R2"
      ],
      "paths": [
        ".agents/skills/plan-project/SKILL.md",
        ".agents/skills/plan-project/references/task-patterns.md",
        ".agents/context.toml",
        ".agents/skills/plan-project/routes.toml",
        "tools/harness/tests/test_project_delivery_defaults.py"
      ],
      "depends_on": [],
      "verification": "기본 선택·라우트 문맥과 gate를 실제 CLI/API 회귀로 확인하고 다섯 제한 시나리오를 자체 검토한다."
    }
  ],
  "decisions": [
    {
      "id": "D1",
      "status": "resolved",
      "operations": [
        "O1"
      ],
      "reason": "현재 사용자가 8단계 안내와 기능 단위 반복을 기본으로 요청했다. 기존 plan-project를 확장하고 새 실행기·그래프 라우트는 만들지 않는다."
    }
  ]
}
```

## Requirements
R1: 문서 기반 구현 요청에서 8단계 안내를 발견·소비한다. R2: 기능별 검증/다음 선택과 요청 범위·중요 결정·시간/차단·미확인을 유지한다.

## Entities
원문 요구·가정·미결정, 기능 묶음, 실제 실행 근거와 잔여 요구를 구분한다. 상태 정본은 기존 task/evidence이며 새 상태 저장소를 만들지 않는다.

## Approach
기존 task-patterns에 체크리스트와 반복 규칙을 두고 SKILL/context/기존 plan 라우트에서 연결한다. 전체 수행 라우트·훅·에이전트 팀은 이번 범위에 필요하지 않다.

## Structure
SKILL은 짧은 요청을 인식하고 원문을 연결한다. context는 plan/implement에만 기본 절차를 선택하고 route 문맥은 requirements/plan에서 읽는다. 현재 에이전트가 판단·수행하며 도구의 자동 품질 판정은 추가하지 않는다.

## Operations
### O1
소유 스킬·읽기 등록·기존 두 plan 라우트만 좁게 확장하고 기본 선택 및 구현 gate 회귀를 추가한다. 문서 가드의 의미는 자체 시나리오로 대조한다.

## Norms
현재 AGENTS·maintain-skills·verify-work·설계/완료 계약을 따른다. 사용자의 현재 체크아웃 작업 지시가 worktree 기본 지침보다 우선한다.

## Safeguards
문서/계획 전용 요청을 구현으로 확대하지 않는다. 중요한 미결정의 무응답을 승인으로 만들지 않는다. 시간 부족으로 필수 기준을 삭제하지 않는다. 설치·브라우저·원격/외부 쓰기는 기존 권한을 유지한다. 제품 UI 변경이 없어 E2E는 비적용이다.
