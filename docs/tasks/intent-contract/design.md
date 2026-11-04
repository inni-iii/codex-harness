# 의도 계약과 발견 기록의 분리

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
        "tools/harness/harness/evidence.py",
        "tools/harness/harness/reasons.py",
        "tools/harness/harness/skill_flows.py",
        "tools/harness/tests/test_intent_contract.py",
        "tools/harness/docs/reasons.md",
        "tools/harness/docs/skill-flows.md",
        "tools/harness/docs/completion.md",
        ".agents/skills/plan-project/references/reasons-canvas.md",
        "docs/tasks/intent-contract/**"
      ],
      "depends_on": [],
      "verification": "같은 반례 RED/GREEN·현재/legacy 정렬·flow·완료 리뷰와 호출자 회귀"
    }
  ],
  "decisions": []
}
```

## Requirements
R1: 목표/범위/수용 조건이 같으면 발견 기록만으로 재정렬/flow 재시작을 하지 않는다. R2: 실제 의도/설계/근거 변경과 결함을 누락한 완료는 계속 거부한다. R3: 이전 파일/완료 이력은 고치지 않고 버전별로 보존한다.

## Entities
설계 의도 지문은 종류·목표·범위·제약·입력·선행 작업·수용 기준/방법이다. 완료 리뷰 지문은 현재처럼 발견 ID도 포함한다. 새 alignment/flow는 v2로 의도 지문을 사용하고 v1은 기존 전체 지문 의미를 유지한다.

## Approach
evidence.contract의 완료 의미를 그대로 두고 intent_contract를 분리한다. reasons 템플릿은 v2, reader는 v1/v2를 명시 판정한다. flow도 v2 기본과 v1 읽기를 유지하며 명시적 restart 때만 v2로 이행한다. 파일 원본·카탈로그/설계 SHA·결정 근거·소스/환경·완료 리뷰의 findings 의무는 유지한다.

## Structure
evidence의 공통 필드와 두 지문, reasons의 정렬 판정/양식, flow의 request/상태/진행 지문에 연결한다. 기존 정본 문서와 REASONS 참조를 갱신한다. 새로운 자동 완료 실행기·대규모 캐시를 만들지 않는다.

## Operations
### O1
실제 네이티브 정렬 템플릿을 준비한 뒤 발견을 추가해 같은 정렬/flow가 유지되지 않는 현상을 동결 반례로 보존한다. 같은 반례와 완료 누락 거부·의도 변경·v1 읽기/명시 전환을 검증한다.

## Norms
현재 사용자가 1번부터 수행하도록 승인했다. 2번은 Git 없이 내용 해시로 문서 변경을 알 수 있음을 설명했고 2/3/4 보완은 후속 순서로 남긴다. 제품 UI가 없어 E2E 비적용이다.

## Safeguards
발견을 지우거나 완료 리뷰를 자동 통과시키지 않는다. 기록만 무시한다는 이유로 의도·설계·원문·권한/환경의 변경 검출을 축소하지 않는다. 과거 v1 파일/완료 이력과 다른 세션 변경을 재작성하지 않는다.
