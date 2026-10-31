---
name: research
description: Investigate technical questions or compare tools using primary evidence, local code, counterexamples and explicit tradeoffs.
---

# 조사에서 결정까지

질문에 대한 답과 선택 근거를 만든다. 조사 요청을 임의의 설치·채택으로 바꾸지 않는다.

1. 현재 요청·관련 과거 원문·프로젝트 결정에서 질문, 제약, 비교 기준을 복원한다.
2. 기존 구현·실패 기록을 먼저 찾고, 실제 용어·호출자·테스트를 따라 탐색한다.
3. 결정에 영향을 주는 외부 사실은 버전·날짜에 맞는 원문으로 확인한다. 기술 사용법은 공식 문서·소스·논문을 우선한다.
4. 가장 강한 대안과 결론을 뒤집을 반례를 확인한다. 문서상 지원과 직접 실행한 결과를 구분한다.
5. 답, 근거, 조건별 차이, 추천 이유, 최대 불확실성, 다음 확인을 남긴다.

| 조건 | 읽을 자료 | 해결할 것 |
|---|---|---|
| 기술 비교·벤치마크·충돌하는 주장 | [근거 판정](references/evidence.md) | 독립성·조건 일치·반증·탈락 근거 |
| 도구 도입 또는 새 공통 기능 | [재사용 판단](references/reuse.md) | 채택/확장/직접 구현의 비용 |
| 큰 자료 집합·복합 질문·검색 누락·RAG 조사 | [검색과 근거 연결](references/retrieval.md) | 질문 분해·출처/버전·문맥 보존·검색/답변 실패 구분 |
| 조사 결과를 프로젝트 문서·주제별 위키에 반영 | [문서 유지관리](../docs-maintenance/SKILL.md) | 기존 주제 통합·출처·모순·읽기 경로 보존 |
| 찾은 파일만으로 맥락이 부족함 | [맥락 탐색](../plan-project/references/context-retrieval.md) | 호출자·공유 경계의 원문 |
| 실험으로 확인해야 함 | [실험 스킬](../experiment/SKILL.md) | 기준선·예산·지표 |

예: 검색 라이브러리를 고를 때 데이터 크기·언어·실행 환경부터 확인하고, 기존 도구와 새 후보를 같은 기준으로 비교한다. 인기 순위를 적합성으로 대신하지 않는다.
지속될 결정은 [결정 템플릿](../plan-project/assets/decision.md), 작업 근거는 [작업 안내](../../../tools/harness/docs/workflows.md)에 연결한다.
작은 조회에 장문의 보고서나 여러 에이전트를 강제하지 않는다. 실제 참여하지 않은 모델의 합의를 주장하지 않는다.

그래프로 절차·검증·재진입을 관리할 때는 [라우트 계약](routes.toml)에서 현재 작업을 고른다. `flow context <실행ID> --read`로 현재 절차와 허용된 다음 경로만 확인한다. 공통 실행 계약은 [스킬 흐름](../../../tools/harness/docs/skill-flows.md)을 따른다.
