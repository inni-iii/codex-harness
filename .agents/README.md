# 작업 지침과 스킬

Codex의 공통 시작 규칙은 루트 [AGENTS.md](../AGENTS.md)에 있다.
작업에 맞는 스킬을 선택하고 해당 SKILL.md가 안내하는 상세 자료만 읽는다.
이 디렉터리 전체를 자동으로 읽는다고 가정하지 않는다.

| 위치 | 관리할 내용 |
| --- | --- |
| `skills/<이름>/SKILL.md` | 적용 조건·필요한 입력·절차·참조를 읽을 조건 |
| `skills/<이름>/references/` | 상세 규칙·예제·예외·실패 조건 |
| `skills/<이름>/assets/` | 해당 작업에 사용하는 문서 양식·설정 예제 |
| `context.toml` | 작업 종류·주제·경로에 따른 읽기 제안 |

프로젝트 개요·워크플로·결정·인수인계 양식은 [plan-project/assets](skills/plan-project/assets)에 있다.
학습 상세 절차와 양식은 [maintain-knowledge](skills/maintain-knowledge/SKILL.md)에 모은다.
실험 양식은 [experiment/assets](skills/experiment/assets), 디자인 양식은 [design-first/assets](skills/design-first/assets),
Playwright 예제는 [e2e-testing/assets](skills/e2e-testing/assets)에 있다.
보안 설계·발견·검사 행렬 양식은 [security-review/assets](skills/security-review/assets)에 있다.
문서 정리·최신화·위키 관리는 [docs-maintenance](skills/docs-maintenance/SKILL.md)에서 필요한 절차를 고른다. 실제 프로젝트 지식은 `docs/`에 저장한다.
검토 지식은 [maintain-knowledge](skills/maintain-knowledge/SKILL.md), 스킬 개선은 [maintain-skills](skills/maintain-skills/SKILL.md), 패키지 관리자·설치는 [setup-environment](skills/setup-environment/SKILL.md)를 사용한다.
양식은 실제 프로젝트에 복사해 작성하고 원본에는 제품별 값을 넣지 않는다.

명령은 레포 루트에서 실행한다.

```sh
python3 tools/harness/run.py context --kind plan --read
python3 tools/harness/run.py context --kind implement --paths backend/items.py --topic api --read
```

스킬을 추가·삭제하면 context.toml도 함께 갱신하고 doctor로 참조를 확인한다.
context는 이 레포의 보조 도구이며 Codex의 기본 스킬 발견 기능과 별개다.
여러 스킬이 공유하는 실행 코드는 [tools/harness](../tools/harness/README.md)에 둔다.
서비스별 요구·도메인 규칙은 [docs](../docs/README.md)에 둔다.
[스킬 작성·검증 방법](../tools/harness/docs/skill-authoring.md)은 이 레포에 있으며 개인 전역 skill-creator 설치를 요구하지 않는다.

`skills/<이름>/routes.toml`은 조건별 절차·검증 계약, [skill-flow.toml](skill-flow.toml)은 스킬:라우트 사이의 허용 이동이다. 공용 [스킬 흐름](../tools/harness/docs/skill-flows.md) 실행기가 호출/복귀·전이·재진입 위치를 저장한다. 현재 라우트의 본문만 선택해서 읽는다.
