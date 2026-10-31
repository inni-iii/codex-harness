# REASONS 구현의 의도와 변경 경계


이 검사를 구현하는 bootstrap 작업이다. 초기 범위/설계는 구현 전 notes와 사용자가 승인한 조사안에 남겼고, 현재 형식 근거는 통합 실행에서 그 동일한 범위를 대조한다. 합성 기능 시험은 설계 준비 전 코드가 없는 상태에서 시작했다.


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
        "R2"
      ],
      "paths": [
        "tools/harness/harness/**"
      ],
      "depends_on": [],
      "verification": "필수 역할·design/review/결정 근거의 SHA·scope/선행/미결정을 start/move/call/restart/재개에서 확인"
    },
    {
      "id": "O2",
      "requirements": [
        "R1",
        "R3"
      ],
      "paths": [
        ".agents/**",
        "AGENTS.md",
        "tools/harness/docs/**",
        "docs/tasks/index.md",
        "docs/tasks/reasons-design-gates/design.md"
      ],
      "depends_on": [],
      "verification": "기존14개 스킬·분석/설계/정렬·docs 변경 분류·양방향 정본·인덱스/선택 읽기와 기존 승인 재사용을 대조"
    },
    {
      "id": "O3",
      "requirements": [
        "R2",
        "R3"
      ],
      "paths": [
        "tools/harness/tests/**"
      ],
      "depends_on": [
        "O1",
        "O2"
      ],
      "verification": "새34개 경계/통합 사례·실제3개 기능 fixture 행동 검사·기존 회귀·같은 R1/R2/R3 RED→GREEN을 확인"
    }
  ],
  "decisions": [
    {
      "id": "D1",
      "status": "resolved",
      "operations": [
        "O1",
        "O2",
        "O3"
      ],
      "reason": "사용자는 직전 SPDD 조사/보완안을 보고 현재 진행해라고 구현을 지시했다. 새 모델 추천·설치·원격 쓰기·자동 승인 흐름을 포함하지 않는다."
    }
  ],
  "references": [
    {
      "path": "tools/harness/docs/spdd-reasons-research.md",
      "sha256": "62f9a950ba9ad8f4299f01f8c956df71b657ec563558c3f803619dd72d450118"
    }
  ]
}

```

## Requirements

R1: plan-project의 REASONS 분석/설계/정렬과 docs 정본·변경 분류를 연결한다. R2: 모든 활성 구현 진입에서 현재 설계/검토·결정/의존 근거와 작업 범위를 확인한다. R3: 기존 승인·작은 변경·독립 작업·이전 완료 이력·선택 읽기를 보존하고 실제 동작으로 검증한다. 수용 기준의 정본은 이 task다.

## Entities

설계 Markdown은7관점과 R/O·범위/선행/결정을 가진다. alignment artifact는 설계 SHA·task 계약·선택 O/coverage·실제 basis/dependency entry 서명을 연결한다. 현재 위치·호출/복귀는 기존 flow, 목표/증거/완료는 기존 task/evidence가 정본이다. 새 도메인 객체 계층이나 상태 장부를 만들지 않는다.

## Approach

기존 typed artifact·strict JSON·canonical path·SHA·source snapshot을 재사용하는 작은 검사기를 추가한다. code gate는 공통 frame 생성에서 처리하며 같은 역할을 재개/판정 때 확인한다. 일반 읽기/문서와 기존 사용자 결정은 과도하게 승인/문서화하지 않는다. 타사 템플릿 일괄 설치보다 기존14개 스킬을 확장한다.

## Structure

reasons.py가 Markdown/metadata·review/coverage·scope·미결정/의존 검사를 맡는다. flow_catalog는 제한된 entry_checks/result_checks를 검증하고 skill_flows의 frame/재개/판정과 context에 연결한다. flow_cli는 pending 검토 양식과 ready 검사를 제공한다. plan/docs 참조와 native skill 생성은 공통 계약을 연결한다. 셸/모델/원격 실행을 추가하지 않는다.

## Operations

### O1
기존 입력 binding과 서명을 재사용하여 구현 진입/재개의 현재 근거·범위·선행 순서를 검사한다. role 검사는 명령/표현식 eval을 받지 않는다.

### O2
7관점의 정본 양식·분석/설계/정렬과 docs intent-update/implementation-sync를 추가하고 필요한 index/참조를 연결한다. 기존14개 entrypoint의 역할을 유지한다.

### O3
현재 요청/설계에서 정상·누락/무관한/낡은 근거·순서/범위·미결정·재시작·선택 읽기를 검사한다. 코드 전 설계 준비를 실제 합성 기능에 적용하고 통합 현재 소스의 회귀로 최종 대조한다.

## Norms

현재 AGENTS·Python/보안/검증·문서 관리의 관련 규칙을 유지한다. 외부 지침을 실행 권한으로 승격하지 않는다. 기존 미커밋 훅·top-down 계획·스킬 정리·과거 완료 기록을 보존한다. 실제 자체 검토를 독립 평가라고 표시하지 않는다.

## Safeguards

서버는 읽기 전용이며 전역 설치·모델 변경·권한 확대·커밋/푸시를 하지 않는다. reason·파일명·형식 통과를 의미적 합의로 바꾸지 않는다. 행동/권한/고정 경계 변경에 editorial을 빌려 설계를 생략하지 않는다. stale/미실행/환경skip을 통과로 바꾸지 않고 실패 근거와 같은 회귀를 보존한다. 현재 API 밖 임의 파일 편집까지 OS 수준으로 차단한다고 주장하지 않는다.
