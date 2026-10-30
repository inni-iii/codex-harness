---
name: plan-project
description: Turn a new project subject or substantial feature into scoped work, project workflow configuration, acceptance criteria and handoffs.
---

# 프로젝트와 작업 구성

새 주제에서는 목표와 확인 가능한 첫 결과를 먼저 정한다.
기존 프로젝트의 작은 수정에는 이미 있는 흐름을 이어 쓴다.

1. 사용자 요청·기존 자료·관련 과거 원문에서 확정 요구, 제안, 미결정을 분리한다.
2. 사용자 동작이나 연구 질문 단위로 완료 기준과 확인 방법을 정한다. 코드 작성만을 완료 기준으로 두지 않는다.
3. 필요한 탐색·설계·실험·구현·검증만 선택하고 앞 결과를 뒤 작업의 입력으로 연결한다.
4. 코드 위치, 공유 경계, 실제 실행 명령을 프로젝트 프로필에 연결한다.
5. 사용자가 결과를 얻는 첫 흐름을 끝까지 연결한 뒤 확장한다. 버튼·파일별로 E2E 완료 단위를 나누지 않는다. 질문과 실패 이유를 다음 작업에 전달한다.

| 조건 | 읽을 자료 |
|---|---|
| 주제 선정→설계→순차 구현·검증과 다음 작업 | [프로젝트 진행](references/project-lifecycle.md) |
| 새 주제의 자료·명령·규칙을 연결 | [워크플로 설정](references/workflow-setup.md) |
| 연구·실험·구현·디버깅·리뷰 분해 | [작업 유형별 흐름](references/task-patterns.md) |
| 큰 레포 탐색·이전 작업 이어하기 | [맥락 탐색과 인수인계](references/context-retrieval.md) |
| 세션/단계 전환·다른 노트북에서 이어받기 | [인수인계](references/handoff.md) |
| 재사용할 실패·사용자 정정·비자명한 해결 | [학습 기록](references/learning.md) |
| 문서 구조 정리·현재 결정 반영·프로젝트 위키 유지 | [문서 관리](../docs-maintenance/SKILL.md) |
| 새 주제의 성능·비용·복구·구조 선택 | [품질 기준과 결정](references/quality-requirements.md) |
| 새 서비스·기능의 보호 자원·권한·도구/외부 경계 | [보안 설계 절차](../security-review/SKILL.md) |
| 여러 세션의 쓰기 작업·독립 변경을 합칠 때 | [격리와 통합 검토](references/collaboration.md) |

Svelte·Python·PostgreSQL은 공통 선택이다. SvelteKit·FastAPI·ORM·DB 버전/확장·배포·디자인·모델을 자동 확정하지 않는다.
주제는 프로젝트 개요, 명령은 workflow.toml, 개별 목표·근거는 task.json과 notes.md에 둔다.
[프로젝트 개요](assets/project-brief.md), [작업 안내](../../../tools/harness/docs/workflows.md)를 사용한다.
3시간짜리 서비스라면 첫 사용자 흐름과 실패 상태를 우선 연결한다. 사용하지 않는 계층이나 전체 디자인 시스템을 선행 작업으로 만들지 않는다.
