# 훅 실패의 제한된 관측

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
        "tools/harness/tests/test_lifecycle_hooks.py",
        "tools/harness/docs/hooks.md",
        "docs/tasks/index.md",
        "docs/tasks/hook-diagnostics/**"
      ],
      "depends_on": [],
      "verification": "실패 단계/코드/시간·민감 원문 비전파·기록 실패·성공 무기록/검사수 보존의 회귀와 메인 통합 검사"
    }
  ],
  "decisions": [
    {
      "id": "D1",
      "status": "resolved",
      "operations": [
        "O1"
      ],
      "reason": "현재 사용자가 향후 실행 비용을 늘리지 않는 작은 진단 보강을 승인했다."
    }
  ]
}
```

## Requirements
R1: 콜백 실패는 단계·고정 원인 코드·시간과 비정상 종료를 보존한다. R2: doctor findings와 source_changed/stale를 구분하고 원문·예외 문자열을 기록하지 않는다. R3: 정상 출력·검사 횟수·모델 호출·권한·기존 도구 경계를 유지한다.

## Entities
진행 정보는 한 콜백의 내부 dict이며 허용한 이벤트와 해시 세션 키·현재 고정 단계만 가진다. 실패 레코드는 세션/이벤트별 최신 JSON 한 파일이다. 기존 정적 보고서는 상태·건수·고정 이유 코드와 시간만 확장한다.

## Approach
현재 main 예외 경계에서 고정 단계/예외 종류를 분류한다. 단계 표시는 기존 함수 호출 직전에만 갱신하며 검사를 다시 돌리지 않는다. 실패할 때만 .runtime/hook-errors에 원자 저장하고 stderr에 코드/경로를 짧게 알린다. 모든 일반 콜백 예외는 비정상 종료로 남기며 KeyboardInterrupt/SystemExit는 성공으로 바꾸지 않는다. 원문 traceback 저장·모델 요약·별도 서비스는 비용과 민감정보 경계 때문에 제외한다.

## Structure
lifecycle_hooks.py의 기존 main/handle/_post에 작은 내부 진행/분류/기록 helper를 둔다. CLI나 훅 정의·주기·신뢰·timeout을 변경하지 않는다. 기록은 기존 runtime_path/atomic 경로 검사를 사용한다.

## Operations
### O1
main의 read/parse/dispatch와 handle의 session·context·checkpoint·정적 검사·상태 저장 단계를 표시한다. _post는 기존 실행 결과를 고정 reason_codes·elapsed_ms로 설명하고 findings와 stale를 짧게 구분한다. 실패 기록 쓰기 자체가 실패하면 diagnostic_unavailable로 알리고 원래 비정상 종료를 유지한다. 정상 무변경 호출은 새로운 파일·모델 호출·검사를 만들지 않는다.

## Norms
사용자 승인 범위와 SSH 읽기 전용·기존 MCP/셸 경계를 유지한다. 검사 오류를 성공으로 바꾸지 않고 타 세션 변경을 덮지 않는다. 현재 에이전트가 요구/오류/공유 경계를 자체 검토한다.

## Safeguards
원문 입력·응답·예외 텍스트·도구 이름·원시 session_id를 저장/출력하지 않는다. 필드는 고정 코드·허용 이벤트·숫자·해시/고정 상대 경로로 제한하고0600 원자 저장한다. 실패 레코드는 최신값 교체로 파일 수를 제한하며 정상 경로의 새 기록은 없다. 외부 호스트가 Python 시작 전 실패하거나 프로세스를 강제 종료/timeout 시 내부 진단은 남지 않을 수 있다. 기존 검사의 stale 판정·실패 exit 정책·stdin 한도·이벤트 신뢰는 유지한다.
