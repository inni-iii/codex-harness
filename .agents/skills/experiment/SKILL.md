---
name: experiment
description: Design or run reproducible experiments comparing hypotheses, model behavior, performance or quality against an explicit baseline and budget.
---

# 재현 가능한 실험

측정으로 답할 질문을 좁히고 기준선과 후보를 같은 조건에서 비교한다.

1. 가설, 입력 범위, 기준선, 주 지표·품질 하한, 예산·중단 조건을 실행 전에 적는다.
2. 이전 결과·실패·조건 차이를 읽고 실행 설정과 결과 파일을 분리한다.
3. 작은 사례로 실행기와 평가기가 작동하는지 먼저 확인한다.
4. 비교 가능한 조건에서 측정한다. 비결정성 때문에 반복이 필요하면 이유·횟수·집계 방법을 사전에 정한다.
5. 실패·시간 초과·제외도 집계한다. 최고 한 번의 결과를 대표값으로 고르지 않는다.
6. 가설을 지지하는 범위와 미측정 조건, 다음 조치를 남긴다.

| 조건 | 읽을 자료 |
|---|---|
| 성능·품질·모델 후보 비교 | [실험 프로토콜](references/protocol.md) |
| 스킬·프롬프트·하네스 자체의 품질 비교 | [하네스 평가](references/harness-evaluation.md) |

[실험 템플릿](assets/experiment.md)을 필요 항목만 채운다.
실제 로컬 반복·지표 파일을 실행/비교할 때는 [실험 도구](../../../tools/harness/docs/experiments.md)를 읽는다.
프로토콜·입력·seed·단위·예산을 먼저 고정하고 experiment run/compare로 원본·실패 포함 집계를 남긴다.
하네스 준비 자체는 유료 호출·원격 변경·무제한 반복의 승인이 아니다.
코드 검사 통과와 실제 작업 성공률 개선을 구분한다. 지침을 조정한 사례와 별도 확인 사례를 분리한다.
