# 한 요청 안에서 검토·수정·회귀를 끝내는 기록

이 문서는 한 요청 안의 검토·수정·재검토와 발견한 반례의 보존을 설명한다.
에이전트가 따르는 절차는 [검토·보완 반복](../../../.agents/skills/verify-work/references/follow-through.md),
기계적으로 확인하는 계약은 harness/completion_review.py에 있다. 추가 AI 팀이나 백그라운드 실행기를 설치하지 않는다.

## 사용자 요청과 에이전트의 책임

사용자는 “이 범위를 점검하고 발견한 문제를 회귀 검사까지 남겨서 완료해줘”처럼 한 번 요청하면 된다.
이 표현만이 유효한 주문은 아니다. AGENTS와 verify-work의 기본 규칙이므로 일반적인 구현·점검·수정 요청에도 적용한다.
에이전트는 권한 범위 안에서 같은 요청의 작업을 이어가고, 끝내기 위한 점검을 사용자의 반복 질문에 맡기지 않는다.

요구/계약에서 확인할 범위를 정하고, 실제 결함을 기록하고, 재현·수정·관련 검사를 이어간다.
최종 상태를 요구·오류 경로·공유 경계·증거에서 다시 검토해 새 문제가 없고 필수 검증이 유효할 때 닫는다.
알 수 없는 모든 결함을 유한 시간에 발견한다는 보장은 아니다. 원래 요청을 무한히 넓히거나 같은 전체 검사를 근거 없이 반복하지 않는다.

## review.json version 2

`evidence review-template <task>`는 기존 수용 기준·리뷰 주체·근거 해시와 함께 verification 객체를 만든다.
새 기본값은 pending이며 자동 통과로 채우지 않는다. 에이전트가 실제 관측 근거로 작성한다.
`evidence verify/complete`의 명령 형태는 유지한다. 따로 “회귀도 남겨”라고 요청할 필요가 없다.

| 필드 | 기록할 것 | 거부하는 상태 |
| --- | --- | --- |
| scope | 이번에 검토한 요구·코드/자료·범위 | 빈 범위 |
| areas | 작업 종류별 각 검토 영역의 checked/not_applicable와 이유 | 빠진/중복 영역·pending·이유 없는 제외 |
| findings | 확인된 결함 ID·증상·원인·상태·회귀 | 미해결 결함·회귀 없는 fixed |
| rounds | 실제 검토 순서·새 발견/처리 ID·관측·증거 | 누락/중복 ID·발견 전 처리·미완료 라운드 |

종류별 areas는 템플릿에 자동으로 선택한다. 모든 종류에 코드 검사를 강제하지 않는다.

| 종류 | 영역 이름 |
| --- | --- |
| research | question_coverage, source_conditions, counterevidence, claim_limits |
| experiment | protocol, input_conditions, measurement, aggregation |
| design | contracts, quality_scenarios, alternatives, verification_plan |
| implement | requirements, failure_paths, shared_boundaries, regressions |
| debug | reproduction, cause, fix_scope, regressions |
| review | requirements, defects, shared_boundaries, evidence |

각 area의 reason에는 무엇을 대조했고 어떤 경계를 확인했는지 적는다. not_applicable은 구체적인 제외 이유가 필요하다.
작은 답변마다 기록 파일을 만들지는 않는다. 실제 결함을 발견했는데 작업 기록이 없다면 의미 있는 작업 하나를 만들어 묶어서 관리한다.

## 발견과 검토 라운드

발견 직후 task.json.findings에 ID를 등록하고 notes.md에 증상·재현 입력·기대 결과·근거를 적는다. 마지막에 리뷰의 findings/rounds로 연결한다.
등록한 ID가 리뷰에서 빠지거나 알 수 없는 ID가 추가되면 완료를 거부한다. 확인한 결함을 빠뜨린 빈 findings 목록으로 닫지 않는다.
작업이 진행되며 증거가 늘면 기존 발견과 관측을 보존하면서 리뷰를 갱신한다.
review-template은 기존 파일을 덮어쓰지 않는다. 이미 파일이 있으면 에이전트가 내용을 읽고 현재 계약/증거와 대조해 갱신한다.
계약 해시는 evidence.contract(task), 증거 해시는 provenance.signature(task['evidence'])로 계산하며 기존 기록을 지우지 않는다.

round에는 id, new_findings, closed_findings, outcome, reason, evidence를 기록한다.
evidence는 task의 실제 증거 ID 목록이다. 새 결함이 있으면 outcome=new_findings,
처리 후 최종 검토에서 새 결함이 없으면 outcome=no_new_findings다.
처음부터 결함이 없다면 findings=[]와 충분한 검토 라운드 하나로 끝낼 수 있다.
같은 녹색 결과를 얻으려고 형식적인 두 번째 테스트 실행을 강제하지 않는다.

예: R1에서 F1을 발견 → 실패 재현·수정·회귀 → R2에서 F1 처리와 관련 경계 재검토, 새 발견 없음.
R2에서 F2가 발견되면 같은 요청 안에서 처리하고 다시 검토한다. 최종 라운드가 new_findings인 채 닫을 수 없다.
중간의 녹색 check 보고서가 새 수정으로 stale이 되면 그 증거를 artifact로 보존하고 새 녹색 check ID를 연결한다.
이전 결함의 after 참조와 수용 기준별 근거도 마지막 관련 검사로 갱신한다. 오래된 통과 결과를 지우거나 현재 통과로 재사용하지 않는다.

## 자동 회귀의 실제 증거

확인한 코드 결함의 기본 regression은 다음 필드를 가진다. 실제 경로/ID/해시는 해당 실행에서 작성한다.

```json
{
  "mode": "automated",
  "test_path": "backend/tests/test_items.py",
  "test_id": "ItemsRegression.test_missing",
  "sha256": "실제 테스트 파일의 SHA-256",
  "check": "items-integration",
  "before": "RED",
  "after": "GREEN"
}
```

RED는 실패한 check report를 artifact 유형으로 연결한 증거 ID다.
GREEN은 통과한 실제 동작 check 보고서를 연결한 증거 ID이며 check 이름이 일치해야 한다.
RED/GREEN의 소스 상태에 같은 경로·같은 해시의 회귀 테스트가 있어야 한다. 테스트를 약화해 녹색으로 바꾸는 것을 막는다.
원본이 남아 있고 실제 실패한 테스트가 있어야 한다. timeout·실행 실패·잘못된 보고서는 동작 결함의 재현으로 인정하지 않는다.
테스트 파일 자체도 고쳐야 한다면 독립된 회귀 사례를 분리하거나 그 한계와 수동 근거를 명시한다. 파일 해시를 임의로 같게 꾸미지 않는다.
특정 test_id가 수정 전에는 실패, 수정 후에는 통과한 것이 식별돼야 한다. 다른 테스트의 실패를 이 반례의 재현으로 쓰지 않는다.
unittest는 -v, pytest/프론트 runner는 이름이 있는 JUnit을 권한다. 원본 로그를 상세히 남겨도 stdout에 전체를 반복 출력할 필요는 없다.
프로젝트 runner의 수집 경로·선택 조건에도 연결하고 실제 해당 사례가 실행되는지 확인한다.

테스트를 이미 고친 뒤라면 과거 상태의 로컬 격리 사본에서 같은 회귀를 실행할 수 있다.
현재 사용자/타 세션 파일을 되돌려 실패를 만들지 않는다. 과거 재현의 한계는 감추지 않는다.

## 연구·설계와 자동화할 수 없는 경우

자동화가 부적절하거나 현재 조건에서 불가능하면 manual을 쓴다.
case(실제 시나리오 artifact ID), before, after, expected, why_not_automated가 필요하다.
수정 전·후 근거는 서로 달라야 하며 시나리오 문서는 수정 후 관측 문서와 함께 관리해도 된다.
source/artifact 유형으로 원문·반례·교정 결과를 연결한다. 코드 테스트처럼 꾸민 단순 문자열 확인을 만들지 않는다.

실행 환경이 없어 관측하지 못한 것을 manual 통과라고 적지 않는다. 필수 확인이 안 되면 findings를 open/blocked로 남겨 완료를 보류한다.
검사기가 수동 관측의 진실성을 대신 판단하지는 않는다. 검토 주체가 이유·기대 결과·실제 근거를 대조해야 한다.

## 범위 밖 결함과 기록의 수명

관련 없는 결함이나 타 세션 소유 문제는 out_of_scope와 원인/경계 이유, follow_up artifact ID를 기록한다.
해당 artifact에는 증상·영향·후속 담당/작업·다시 읽을 조건을 남긴다. 원래 요구를 제외해 통과시키는 우회로 쓰지 않는다.
전체가 해결됐다고 말하지 않고 최종 보고에 남은 범위를 구분한다.

과거 review v1 완료 이력은 당시 기록으로 읽지만 현재 재검증/완료에는 review v2가 필요하다.
완료된 과거 작업의 코드 테스트가 나중에 진화했다고 옛 완료를 모두 실패 처리하지 않는다.
당시 보고서 안의 테스트 해시·원본은 보존하며 현재 증거로 재사용할 때는 현재 파일도 대조한다.

재사용할 예방 원칙은 [학습 절차](../../../.agents/skills/plan-project/references/learning.md)를 따라 프로젝트 자료나 해당 스킬에 연결한다.
한 번의 반례를 근거 없이 모든 프로젝트의 전역 규칙으로 만들지는 않는다.
