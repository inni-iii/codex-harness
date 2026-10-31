---
name: plan-project
description: Turn human-defined goals and milestones into requirements, success criteria, evidence-based gap assessments and scoped work; replan project work and handoffs as conditions change.
---

# 프로젝트와 작업 구성

사람이 정한 목표·아키텍처 경계·마일스톤에서 요구·성공 조건·현재 갭·작업을 도출한다.
기존 프로젝트의 작은 수정에는 이미 있는 흐름을 이어 쓰며 질문마다 전체 계획을 만들지 않는다.

1. 사용자 요청·기존 자료·관련 과거 원문에서 확정 요구, 제안, 미결정을 분리한다.
2. 관련 마일스톤에서 사용자 동작이나 연구 질문 단위의 요구·성공 조건·확인 방법을 도출한다. 새 제품 결정을 기존 요구인 것처럼 확정하지 않는다.
3. 시작할 때 이전 계획의 갭을 현재 코드·계약·검증 근거와 비교한다. 요청 범위에서 필요한 탐색·설계·실험·구현·검증을 선택하고 앞 결과를 뒤 작업의 입력으로 연결한다.
4. 코드 위치, 공유 경계, 실제 실행 명령을 프로젝트 프로필에 연결한다.
5. 기능 묶음을 구현·검증하고 어떤 성공 조건의 갭이 줄었는지 근거를 연결한다. 남은/새 갭과 다음 작업을 갱신한다. 버튼·파일별로 E2E 완료 단위를 나누지 않는다.

| 조건 | 읽을 자료 |
|---|---|
| 상위 목표·마일스톤 분해, 작업 전후 갭 재평가, 다음 작업 선택 | [프로젝트 진행](references/project-lifecycle.md) |
| 코드 전 의도/경계·도메인·대안·REASONS 설계/정렬 | [설계와 정렬](references/reasons-canvas.md) |
| 새 주제의 자료·명령·규칙을 연결 | [워크플로 설정](references/workflow-setup.md) |
| 연구·실험·구현·디버깅·리뷰 분해 | [작업 유형별 흐름](references/task-patterns.md) |
| 큰 레포 탐색·이전 작업 이어하기 | [맥락 탐색과 인수인계](references/context-retrieval.md) |
| 세션/단계 전환·다른 노트북에서 이어받기 | [인수인계](references/handoff.md) |
| 재사용할 실패·사용자 정정·비자명한 해결 | [교훈·학습 관리](../maintain-knowledge/SKILL.md) |
| 문서 구조 정리·현재 결정 반영·프로젝트 위키 유지 | [문서 관리](../docs-maintenance/SKILL.md) |
| 새 주제의 성능·비용·복구·구조 선택 | [품질 기준과 결정](references/quality-requirements.md) |
| 새 서비스·기능의 보호 자원·권한·도구/외부 경계 | [보안 설계 절차](../security-review/SKILL.md) |
| 여러 세션의 쓰기 작업·독립 변경을 합칠 때 | [격리와 통합 검토](references/collaboration.md) |

Svelte·Python·PostgreSQL은 공통 선택이다. SvelteKit·FastAPI·ORM·DB 버전/확장·배포·디자인·모델을 자동 확정하지 않는다.
주제는 프로젝트 개요, 명령은 workflow.toml, 개별 목표·근거는 task.json과 notes.md에 둔다.
[프로젝트 개요](assets/project-brief.md), 필요한 경우 [목표·갭 계획 양식](assets/project-plan.md), [작업 안내](../../../tools/harness/docs/workflows.md)를 사용한다.
3시간짜리 서비스라면 첫 사용자 흐름과 실패 상태를 우선 연결한다. 사용하지 않는 계층이나 전체 디자인 시스템을 선행 작업으로 만들지 않는다.

그래프로 절차·검증·재진입을 관리할 때는 [라우트 계약](routes.toml)에서 현재 작업을 고른다. `flow context <실행ID> --read`로 현재 절차와 허용된 다음 경로만 확인한다. 공통 실행 계약은 [스킬 흐름](../../../tools/harness/docs/skill-flows.md)을 따른다.
