# 훅 실패의 소비와 해결 연결

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
        "tools/harness/harness/lifecycle_hooks.py",
        "tools/harness/harness/hook_recovery.py",
        "tools/harness/harness/hook_sessions.py",
        "tools/harness/harness/cli.py",
        "tools/harness/tests/test_hook_feedback.py",
        "tools/harness/tests/test_hook_recovery.py",
        "tools/harness/docs/hooks.md",
        "tools/harness/docs/architecture.md",
        "AGENTS.md",
        ".agents/skills/verify-work/references/follow-through.md",
        "docs/tasks/index.md",
        "docs/tasks/hook-recovery/**"
      ],
      "depends_on": [],
      "verification": "실패 기록의 전후 main 회귀·중복 억제/재개·해결 근거·세션/권한/민감 경계와 관련 등록 검사"
    }
  ],
  "decisions": [
    {
      "id": "D1",
      "status": "resolved",
      "operations": [
        "O1"
      ],
      "reason": "현재 사용자 정정으로 기록 소비·조치·해결 확인 연결을 보강한다. 실행 권한과 비용 조건을 유지한다."
    }
  ]
}
```

## Requirements
R1: 다음 성공 Pre/Post 및 SessionStart에서 현재 세션의 미해결 실패를 짧은 모델 맥락으로 전달한다. R2: status/resolve로 진단 해시와 실제 task 근거를 연결하고 해결/새 실패를 구분한다. R3: 모델/검사/재시도·권한을 추가하지 않고 정상 출력과 보안을 보존한다.

## Entities
기존 hook-errors의 세션/허용 이벤트별 최신 진단 최대6개를 읽는다. 새 hook-receipts는 통지한 진단 해시와 해결한 진단/근거 해시만 저장한다. 현재 에이전트는 원인·수정·실제 재검증의 의미를 판단하고 task 증거를 등록한다. task/flow와 오류 원문을 복제하지 않는다.

## Approach
기존 성공 콜백 출력에 best-effort 알림을 병합한다. 실패 파일이 없으면 고정6개 존재 확인만 수행하며 doctor/모델을 호출하지 않는다. 새 실패 해시만 Pre/Post에서 통지하고 미해결은 SessionStart/Stop에서 다시 안내한다. 알림 전달은 기존 세션 잠금·별도 작은 receipt로 중복을 억제하되 원래 권한 결정을 가리거나 바꾸지 않는다. 기록만 쌓는 대안은 사용자 정정에 미달하고 자동 모델 루프는 비용/권한 때문에 제외한다.

## Structure
hook_recovery.py가 읽기·고정 필드 검증·receipt/모델 맥락·해결 확인을 맡는다. main은 성공 출력에만 연결하고 정적 findings도 추가 맥락으로 전달한다. hook_sessions의 status에 미해결을 포함하고 CLI resolve는 기존 evidence 검증을 재사용한다. AGENTS/verify-work가 실제 읽기·보완·재검증·증거 해결을 수행할 조건을 연결한다.

## Operations
### O1
F1을 실제 실패와 후속 성공 main으로 재현한다. 알림에는 고정 단계/코드/상대 경로와 조치만 넣고 payload/임의 필드를 재주입하지 않는다. resolve는 현재 진단 해시 일치·등록된 task 근거 무결성을 확인한다. 근거가 실제 원인 해결을 입증하는지는 에이전트가 판단하며 단순 파일 존재를 자동 진실 판정으로 표현하지 않는다. 새 진단은 이전 receipt와 해시가 달라 다시 미해결이 된다.

## Norms
에이전트는 알림을 받으면 원문 진단·현재 소유권·권한을 확인하고 허용된 수정과 관련 재검증을 수행한다. 범위 밖/권한 차단은 task에 사유와 다음 행동을 남기며 미해결을 유지한다. 무작정 원 도구를 반복하거나 사용자에게 같은 요청을 다시 시키지 않는다.

## Safeguards
정상 출력·검사 횟수·기존 deny/종료 정책을 유지한다. 기록/receipt 읽기 실패는 주 동작의 권한 판정을 약화시키지 않는다. 허용 이벤트/단계/코드·해시/작은 레코드만 읽고 세션 식별이 불가능한 공용 진단은 임의로 현재 세션에 귀속하지 않는다. 알림/해결은 모델 실행·자동 수정이 아니며 실제 에이전트의 증거 검토가 필요하다.
