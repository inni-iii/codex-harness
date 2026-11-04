# 단계별 사용자 검토의 변경 계약

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
        "tools/harness/tests/test_project_delivery_defaults.py",
        ".agents/skills/plan-project/references/project-lifecycle.md"
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
      "reason": "최신 사용자 원문은 각 단계 결과를 직접 본 뒤 다음 진행을 결정하는 방식이다. 이전 자동 진행 기본 해석을 대체한다."
    }
  ]
}
```

## Requirements
R1: 요구 문서 기반 요청은 1단계부터 시작해 각 단계 결과 후 사용자 다음 지시를 기다린다. R2: 기능별 구현/검증/다음 선택에 검토 경계를 두고 계획 전용·명시적 자율 전환·실패·시간 경계를 유지한다.

## Entities
현재 단계·사용자 검토·다음 지시·기능 묶음을 구분한다. 실제 원문과 기존 task/evidence가 근거이며 새로운 모드 엔진/상태 저장소는 만들지 않는다.

## Approach
기존 스킬·task-patterns·기본 선택·계획 route를 유지하며 안내의 진행 방식만 최신 요청으로 교정한다. 전체 자율 진행은 사용자가 명시적으로 맡긴 범위에 한한다.

## Structure
SKILL에 기본 대기를 명시하고 task-patterns의 8단계 및 lifecycle의 기존 무중단 설명을 같은 의미로 맞춘다. context는 원문 선택, flow는 기존 경로/권한 가드를 유지한다. 실제 대기는 현재 에이전트의 지침 수행이며 자동 승인 인증 기능은 아니다.

## Operations
### O1
소유 스킬·참조·선택 등록·계획 route와 회귀만 보완한다. 사용자 검토 시나리오와 기존 구현 gate를 대조한다.

## Norms
최신 사용자 정정이 이전 자동 진행 요구 해석보다 우선한다. 현재 공간에서 진행하라는 지시·기존 동시 변경 보존·설계/검증/완료 계약을 유지한다.

## Safeguards
침묵·시간 경과·자료 조회를 다음 승인으로 만들지 않는다. 계획/설계만이면 구현하지 않는다. 다음 기능이나 단계의 독립 작업을 미리 수행하지 않는다. 작은 기존 수정에 8단계를 강제하지 않는다. 새 훅·모델·권한·원격 쓰기를 추가하지 않는다. UI 변경이 없어 제품 E2E 비적용.
