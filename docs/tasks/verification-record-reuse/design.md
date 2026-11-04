# 기록과 코드 검증의 경계

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
        "tools/harness/harness/record_scope.py",
        "tools/harness/harness/core.py",
        "tools/harness/harness/checks.py",
        "tools/harness/harness/evidence.py",
        "tools/harness/harness/skill_flows.py",
        "tools/harness/harness.toml",
        "tools/harness/tests/test_record_reuse*.py",
        ".agents/skills/docs-maintenance/SKILL.md",
        ".agents/skills/docs-maintenance/references/navigation.md",
        ".agents/skills/verify-work/references/evidence.md",
        "tools/harness/docs/verification.md",
        "tools/harness/docs/completion.md",
        "tools/harness/docs/skill-flows.md",
        "docs/tasks/verification-record-reuse/**"
      ],
      "depends_on": [],
      "verification": "독립 기록 회귀 RED/GREEN·입력 보존/legacy 반례·최종 통합 검사"
    }
  ],
  "decisions": []
}
```

## Requirements
R1: 무관한 작업 기록으로 코드 검사를 반복하지 않는다. R2: 실제 입력/요구/설정·환경/권한 변경과 과거 증거 무결성을 검출한다. R3: 인덱스 중심의 필요한 원문만 읽고 반복 전체 로드를 하지 않는다.

## Entities
작업 기록은 docs/tasks 아래 Markdown과 task/review JSON이다. 실행 코드·설정·다른 JSON은 계속 소스다. 입력에서 독립이라고 선언한 검사만 제외 정책을 사용한다.

## Approach
공통 record_scope 정책을 cache/완료/flow에서 재사용한다. 전체 원본 해시는 보존하며 새 명시 정책에서만 무관 기록을 제외한다. 검사 paths/프로젝트 참조와 task 입력·scope·증거·선행 작업의 기록은 보호한다. 모르는 검사와 옛 보고서는 기존 보수적 전체 비교를 유지한다.

## Structure
record_scope는 분류/보호/필터만 담당한다. core 지문·checks 보고서 정책·evidence 현재 비교·flow 소스에 연결한다. 기존 인덱스/본문 선택 코드는 재사용하고 지침만 명확히 한다.

## Operations
### O1
같은 frozen 테스트에서 무관한 기록 추가 후 cache/완료/flow 무효화를 재현한다. opt-in 하네스 Python 검사만 새 경계를 사용하며 관련 입력 변경의 거부를 검증한다.

## Norms
현재 사용자 승인으로 진행한다. 새로운 모델·설치·원격 쓰기·추가 자동 완료 프레임워크를 만들지 않는다. 매 문서 본문을 기본 읽기에 넣지 않고 필수/보안·선택한 원문은 유지한다.

## Safeguards
원본 보고서·완료 이력을 고치지 않는다. 임의 docs 전체 제외나 task scope만으로 소스 검출을 축소하지 않는다. 알 수 없는 정책·설정·부정 입력은 실패한다. 브라우저 UI가 없어 E2E 비적용.
