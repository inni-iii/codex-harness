# 작업 기록과 이어서 진행하기

작업은 세션이 아니라 목표·결과·검증 기준이 있는 단위다. 작은 요청은 대화에서 간단히 처리할 수 있다.
여러 세션을 이어가거나 다른 작업으로 결과를 넘겨야 할 때 파일을 사용한다.

```sh
python3 tools/harness/run.py task compare-api-clients --kind research --goal "API 클라이언트 후보 비교" --acceptance "공식 근거와 제약을 비교한다"
```

docs/tasks/compare-api-clients/task.json과 notes.md를 생성하며 기존 파일은 덮어쓰지 않는다.
입력·범위·제약·선행 작업·결정·미해결 질문·완료 기준별 확인 방법과 근거를 기록한다.
태스크의 원문·결과는 공유 파일이므로 비밀값·개인 인증·무관한 세션 내용을 넣지 않는다.
민감한 상세 자료는 Git 제외 경로에 두고 공유 가능한 근거만 연결한다.
상태는 planned/in_progress/needs_revision/blocked/complete로 기록한다.
완료 기준의 상태는 pending/passed/failed/unverified다. 새 기록은 version 2이며 evidence ID를 실제 파일·유형·해시에 연결한다.
완료에는 종류별 최소 증거, 모든 기준의 확인 방법, 기준별 이유가 있는 리뷰가 필요하다.
[완료와 증거 연결](completion.md)의 evidence add → review-template → verify/complete 절차를 사용한다.
doctor는 구조와 완료 기록의 무결성을 확인하지만, 연구 결론의 진실성이나 실제 제품 전체를 자동 판정하지는 않는다.

## 공통 진행

시작할 때 context --kind와 실제 경로/주제로 필요한 스킬·참조 원문을 읽는다.
새 주제의 자료·도메인 규칙·실제 검사 명령은 [프로젝트 프로필](project-workflows.md)로 연결한다.
주제와 개별 task를 구분하고, 작은 수정마다 새 프로젝트 프로필을 만들지 않는다.

1. 요청과 관련 원문·프로젝트 자료를 읽고 목표·현재 상태·경계를 복원한다.
2. 사용자 결과 기준의 의미 있는 작업 묶음과 확인 방법을 정하고, 이번 검증 범위·E2E 수행 여부와 시점을 먼저 알린다. 버튼·파일별로 기능 완료 단위를 지나치게 좁게 나누지 않는다.
3. 연구·실험·설계·구현 중 필요한 수행을 한다. 새 사실이 전제를 바꾸면 계획도 바꾼다.
4. 결과를 요구와 대조하고 관련 검사·리뷰·반례를 확인한다.
5. 수정했다면 영향을 받은 부분을 다시 확인하고 결정·근거·다음 행동을 남긴다.

모든 단계의 재승인을 기본으로 요구하지 않는다. 자동으로 가능한 범위는 계속 진행하고
결과를 바꾸는 미확정 선택만 확인한다. 과거 승인이나 도구 접근이 새로운 외부 쓰기 권한은 아니다.

## 작업별 근거

| 종류 | 확인 방법 | 이어갈 내용 |
| --- | --- | --- |
| 연구 | 현재 원문·출처·반례·독립 근거·불확실성 | 결론, 후보, 선택 이유, 미해결 질문 |
| 실험 | 기준선·동일 조건·버전·필요한 반복·변동 | 데이터/코드/설정 식별자와 결과, 실패·탈락 |
| 설계 | 사용자 시나리오·대안·경계·오류/복구·인터페이스 | 선택과 제약, 구현 순서, 검증 기준 |
| 구현 | 기능 단위 연결·관련 테스트·사용자 흐름 | 변경과 검사 증거, 남은 결함 |
| 검토 | 요구사항과 독립적인 관점, 실제 결과 대조 | 근거 있는 발견·영향·보완 내용 |

모델 추천은 기존 `python3 tools/harness/run.py route ...`를 사용한다.
기본 작업은 현재 대화창 모델로 수행한다. 별도 실행 방식을 명시적으로 선택한 경우에만 [모델 실행 계약](execution.md)의 run/chat을 사용한다. ready 추천, 작업 프로세스 종료, 요구 충족을 각각 확인한다. 자동 에이전트 팀·제품 수용 판단·재작업 오케스트레이터는 아직 없다.
작업형·위험도만으로 고정 모델을 추가하지 않고 지원되는 모델·effort와 제약을 함께 확인한다.

새 프로젝트는 [개요](../../../.agents/skills/plan-project/assets/project-brief.md), 중요 선택은 [결정](../../../.agents/skills/plan-project/assets/decision.md),
실험은 [실험 기록](../../../.agents/skills/experiment/assets/experiment.md)을 필요한 만큼 사용한다.
디자인 설정은 사용자와 [디자인 기준](../../../.agents/skills/design-first/assets/design-system.md)을 먼저 정한 뒤 프론트 작업에 적용한다.

## 검토·인수인계·규칙 보완

코드 완료 검토는 context --kind review로 [리뷰 절차](../../../.agents/skills/verify-work/references/review.md)를 읽고 요구 충족과 결함·회귀를 구분한다.
유효한 검사 결과는 재사용하고 새 결함 가설·조건 변화가 있을 때만 추가 확인한다.
인증·권한·업로드·비밀값·실행 설정 변경에는 [보안 스킬](../../../.agents/skills/security-review/SKILL.md)에서 관련 경계를 확인한다.

긴 작업의 단계 전환에서는 notes.md에 [인수인계 템플릿](../../../.agents/skills/plan-project/assets/handoff.md)의 필요한 항목을 채운다.
여러 세션의 수정은 [격리·통합 절차](sessions.md)와 [변경 의도 판단](../../../.agents/skills/plan-project/references/collaboration.md)을 따르고, 합친 결과를 검사한다.
이어받을 때 context --kind plan --topic resume --project <프로필>로 프로젝트의 실제 체크포인트와 절차를 읽는다.
프로필에 체크포인트 문서를 등록해야 프로젝트 내용까지 선택된다. 공통 절차만으로 이전 상태를 자동 복원하지는 않는다.

반복 실패·비자명한 해결·사용자 정정은 [학습 기록](../../../.agents/skills/plan-project/assets/lesson.md)에 적용/제외 조건과 근거를 남긴다.
context --kind review --topic learning으로 규칙 보완 절차를 읽고, 프로젝트에 남길 내용은 context.rules로 연결한다.
검토 상태·공유·조건별 조회는 [지식 관리](knowledge.md)의 catalog로 연결한다. workflow 문서는 프로젝트 사실/진행 자료, catalog는 재사용 교훈을 담당하며 같은 규칙의 별도 정본을 만들지 않는다.
기존 학습 훅은 안내와 메타데이터만 처리한다. 대화 수집·백그라운드 학습·개인 전역 승격을 추가하지 않으며 자동 사실 판정·규칙 채택으로 표현하지 않는다.
