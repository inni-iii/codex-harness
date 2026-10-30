---
name: maintain-skills
description: Create or improve native repository skills from a concrete workflow, reviewed lesson or reference, then register discovery and validate realistic use.
---

# 스킬 작성·개선

반복 작업의 재사용, 기존 스킬의 잘못된 선택·누락을 고칠 때 적용한다.
기존 스킬의 조건부 참조로 해결되면 그곳을 보완한다.

1. 실제 사용자 요청·기대 결과를 정하고 기존 스킬·지식·실패에서 중복과 충돌을 찾는다.
2. 외부 예제의 본문·참조·호출 코드를 읽는다. Codex라는 이름만으로 경로·훅·명령의 지원을 판단하지 않는다.
3. 짧은 name/description과 판단·실패 조건을 작성한다. 긴 조건별 내용은 references로 연결한다. 개인 경로·고정 모델·불필요한 승인 절차는 옮기지 않는다.
4. [작성 도구](../../../tools/harness/docs/skill-authoring.md)의 skill create/from-knowledge로 생성·등록한다. 기존 스킬은 필요한 부분만 수정한다.
5. 실제 요청의 정상·오류·경계 사례에서 선택된 원문과 결과를 확인한다. 문법 통과와 작업 판단 품질을 구분한다.
6. AGENTS 지도·설명서를 갱신하고 doctor·context·행동 검증 근거를 남긴다.

Git 이력은 후보 근거 중 하나다. 커밋 빈도만으로 좋은 규칙이라고 정하지 않는다.
커밋이 없으면 요구·코드·검증된 해결 기록을 사용한다. 생성을 위해 커밋·PR·외부 계정 연결을 만들지 않는다.
원본 지식의 대체·조건 변경을 추적해 생성한 스킬도 유지한다.
