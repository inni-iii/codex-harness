# 프로젝트 자료

아직 프로젝트 주제는 정해지지 않았다.
주제가 정해지면 프로젝트별 하위 폴더에 목표·요구사항·결정·연구 결과·디자인 기준을 저장한다.
`project` 명령은 그 프로젝트의 `index.md`·`brief.md`·`security.md`·draft `workflow.toml`을 만든다.
프로젝트를 실제로 만들면 이 문서에 해당 `index.md` 링크를 추가한다. 현재 서비스 프로젝트 항목은 없다.
[개요 템플릿](../../.agents/skills/plan-project/assets/project-brief.md)과 [디자인 템플릿](../../.agents/skills/design-first/assets/design-system.md)을 활용한다.
[보안 설계 양식](../../.agents/skills/security-review/assets/security-profile.md)은 project 명령이 security.md로 생성한다. 실제 서비스의 자원·권한·실패 조건을 채우고 미해결 위험과 검사 근거를 연결한다.
코드 위치는 시작 시 정한다. 별도 서비스 저장소를 전제하지 않는다.
인증·비밀값·개인 세션 원문은 공유 문서에 복사하지 않는다.

## 주제부터 구현까지

[프로젝트 진행 절차](../../.agents/skills/plan-project/references/project-lifecycle.md)에 따라
주제/요구 → 필요한 조사 → 설계/결정 → 선행 작업이 있는 구현 순서 → 기능별 구현/검증 → 다음 작업을 연결한다.
현재 상태는 task.json과 실제 근거가 정본이며, 프로젝트 인덱스는 단계별로 필요한 문서만 찾는 지도다.
설계·구현 계획 파일은 실제로 필요할 때 작성하고 인덱스와 workflow의 읽기 조건에 연결한다.
의존 관계를 기록해도 자동으로 작업 순서를 실행하는 기능이 생기지는 않는다.
