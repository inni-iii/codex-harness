---
name: maintain-knowledge
description: Record, review, retrieve and share project lessons or common rules with provenance, applicability and supersession. Use for persistent knowledge maintenance and repeated corrections.
---

# 작업 경험을 검토 가능한 지식으로 관리

현재 작업의 진행 상태는 notes/인수인계에, 조건이 있는 재사용 교훈은 지식 catalog에 둔다.

1. 현재 요청과 과거 원문에서 관측·사용자 결정·추론을 구분한다. 기록이 과거 원문 확인을 대체하지 않는다.
2. knowledge search/list로 기존 지식·중복·대체된 규칙을 찾는다. 적용/제외 조건과 프로젝트 범위를 정한다.
3. [지식 명세와 명령](../../../tools/harness/docs/knowledge.md)에 따라 candidate로 기록한다. 전체 대화·도구 응답·비밀값은 수집하지 않는다.
4. 실제 사례·회귀·공식 계약을 확인하고 이유와 증거를 연결해 evaluated/adopted로 검토한다. 해시나 모델 confidence가 내용의 진위를 판정하지 않는다.
5. 공통화는 프로젝트 기록을 보존한 채 별도 후보로 만든다. 반복 횟수만으로 공통 적용하지 않는다.
6. 변경된 규칙은 같은 범위의 채택된 대체 기록을 연결해 superseded로 남긴다. 관련 스킬·프로젝트 규칙도 검토한다.

bundle은 import --dry-run으로 범위·충돌을 확인한다. 가져온 기록은 candidate이며 자동 적용하지 않는다.
context는 범위·kind/topic/path 선택 조건·현재 증거가 맞는 adopted만 선택한다. 자연어 적용/제외 조건의 충족 여부는 원문에서 판단한다. 공통 절차를 스킬로 만들 때는 [스킬 관리](../maintain-skills/SKILL.md)를 따른다.
학습용 SessionStart/PreCompact/Stop 훅은 검토 지식 안내와 작업 메타데이터를 연결한다. 이 세 훅은 추가 모델 호출이나 자동 사실 판정을 하지 않는다. UserPromptSubmit 라우팅 훅은 현재 등록하지 않으며 일반 작업에 라우터를 강제하지 않는다.
