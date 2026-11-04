# 짧은 검증 요청의 기본 동작

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
        ".agents/skills/verify-work/SKILL.md",
        ".agents/skills/verify-work/references/acceptance.md",
        ".agents/skills/verify-work/routes.toml",
        ".agents/context.toml",
        ".agents/skill-flow.toml",
        "tools/harness/docs/verification.md",
        "tools/harness/docs/skill-flows.md",
        "tools/harness/tests/test_verification_defaults.py",
        "docs/tasks/verification-defaults/**",
        "docs/tasks/index.md"
      ],
      "depends_on": [],
      "verification": "기본 review context의 원문 선택, 실제 flow의 request-only 진입/수리 gate와 실제 제한별 시나리오 및 전체 등록 회귀"
    }
  ],
  "decisions": [
    {
      "id": "D1",
      "status": "resolved",
      "operations": [
        "O1"
      ],
      "reason": "현재 사용자가 긴 프롬프트 없이 검증 절차가 적용되도록 요청했다. 기존 네이티브 스킬/종료 알림을 재사용하고 새 훅/모델 호출은 추가하지 않는다."
    }
  ]
}
```

## Requirements
R1: “검증해줘” 요청을 현재 대상의 수용 검증으로 해석해 정상/실패·회귀·실제 실행·구조·보안·관련 E2E를 선별한다. R2: 대상이 명확하면 진행하고 요청만으로 읽기 검증에 진입하되 실제 수리는 현재 권한/설계 정렬을 따른다. R3: 문서/조사·명시 제한·새 환경·재사용 조건을 지키고 추가 모델/훅/검사 루프를 만들지 않는다.

## Entities
기존 verify-work가 단일 소유자다. 새 acceptance 참조는 짧은 요청의 기본 해석·적용/제외와 결과 계약을 담당하고 상세 테스트 작성은 기존 언어/보안/E2E 스킬을 따른다. inspect는 request-only 읽기 검토, check/repair는 기존 구현 검증/수리 gate를 유지한다.

## Approach
네이티브 설명에 짧은 요청을 명시하고 SKILL에서 기본 계약을 먼저 읽는다. context의 review에는 작은 기본 참조를 선택한다. inspect는 현재 대상/정상·실패/증거를 확인하고 artifact로 결과를 보고한다. 결함 수정이 허용된 경우 기존 repair를 필요한 설계/정렬 입력으로 호출한다. 모든 코드를 고정 키워드/훅으로 자동 실행하거나 새로운 프롬프트 모델을 호출하는 방식은 제외한다.

## Structure
acceptance.md를 소유 스킬에 추가하고 SKILL/context/routes/허용 이동 및 사용 문서를 맞춘다. 기존 check도 같은 기본 계약을 읽는다. 추가 훅/글로벌 설정/AGENTS 변경은 필요하지 않다. 검사 범위 선택과 실행 판단은 현재 에이전트가 한다.

## Operations
### O1
기본 context와 inspect 경로 부재를 동일 회귀로 실패시킨다. 발견·선택·소비·허용 이동을 연결한 뒤 docs/코드/권한/설정 부족 시나리오를 대조하고 관련 및 전체 검사로 확인한다.

## Norms
현재 대화·명시 대상·연결한 task/프로젝트에서 범위를 복원한다. 대상이 복수여서 결과가 달라질 때만 질문한다. “검증만/수정하지 마” 같은 제한을 우선하며 단순 정적 검사로 실제 동작/보안을 확인했다고 하지 않는다. 관련 정상·실패와 원래 계약/회귀를 확인한다.

## Safeguards
요청보다 큰 재설계·인증 방식 변경·원격 쓰기·유료 모델·설치를 임의 실행하지 않는다. 검사 없음/미실행/환경 차단을 통과로 바꾸지 않는다. 문서/조사에는 앱 기동/E2E를 강제하지 않고 유효한 결과를 재사용한다. 새 훅/모델 호출/도구별 전체 검사 루프와 의미적 품질 자동 보장은 추가하지 않는다.
