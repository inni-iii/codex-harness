# Docker 컨테이너 스킬의 의도와 연결

```json
{
  "version": 1,
  "kind": "reasons-design",
  "profile": "structural",
  "requirements": ["R1", "R2", "R3", "R4"],
  "operations": [
    {
      "id": "O1",
      "requirements": ["R1", "R2", "R3", "R4"],
      "paths": [".agents/skills/docker-containers/**", ".agents/context.toml", ".agents/skill-flow.toml", ".agents/skills/setup-environment/SKILL.md", ".agents/README.md", "AGENTS.md", "README.md", "tools/harness/docs/skill-authoring.md", "tools/harness/docs/reasons.md", "tools/harness/tests/test_container_skill.py", "docs/tasks/index.md", "docs/tasks/docker-container-skill/**"],
      "depends_on": [],
      "verification": "네이티브 스킬 검증·doctor·선택기/flow/Compose 계약 검사·정상/읽기전용/오류/권한 시나리오와 영향받는 회귀를 확인한다"
    }
  ],
  "decisions": [
    {"id": "D1", "status": "resolved", "operations": ["O1"], "reason": "사용자가 별도 프로젝트에서 재사용하는 Docker 스킬 생성을 명시했다. 이 하네스 실행 인프라는 만들지 않는다."},
    {"id": "D2", "status": "resolved", "operations": ["O1"], "reason": "setup-environment의 패키지/lock 조사와 다른 책임인 이미지·Compose·컨테이너 수명/진단을 docker-containers가 소유한다."},
    {"id": "D3", "status": "resolved", "operations": ["O1"], "reason": "정적 배포를 강제하지 않는다. 실제 프로젝트의 frontend 런타임·패키지 관리자·DB 버전을 읽고 선택하며 이미지/실행 예제는 출발점으로만 제공한다."}
  ]
}
```

## Requirements

R1: 사용자 요청대로 다른 프로젝트에서 쓰는 Docker 스킬을 제공한다. 이미지와 실행 환경을 여기서 자동 생성/가동하지 않는다.
R2: Docker 주제/실제 경로로 발견되고 무관한 앱/문서 작업에 기본 로드되지 않는다. inspect/design/diagnose는 읽기/설계, configure는 현재 설계·정렬과 실제 검증을 요구한다.
R3: 이미지 빌드·Compose topology·준비/재연결·volume·secret·architecture·runtime 권한·복구를 연결한다. 패키지 설치/앱·DB·브라우저 검증의 정본은 기존 스킬에 둔다.
R4: 선택·라우트·예제와 실제 요청 시나리오를 확인하고 정적 통과와 build/run/E2E를 구분한다.

## Entities

대상 프로젝트, manifest/lock, 이미지/context, Compose project/service/network/volume, secret 파일, 상태 확인, migration, 실행 보고서가 관련 개념이다. 스킬은 절차이고 background executor가 아니다. 대상 앱과 실행 자원은 사용자가 정한 프로젝트가 소유한다.

## Approach

기존 setup-environment를 거대한 DevOps 스킬로 확장하는 대안보다 별도 docker-containers를 만들고 필요한 단계에서 기존 스킬로 연결한다. 복제된 운영 명령·고정 버전·Svelte 정적 강제·CI/SSH 배포·항상 다중 DB는 제외한다. 새 Python CLI/오케스트레이터는 만들지 않는다.

## Structure

SKILL은 범위/라우트와 판단을, references는 images/compose/verification의 조건별 절차를, assets는 프로젝트 명세 양식과 명시적 컨테이너 계약의 예제 Compose를 소유한다. context는 주제·Docker 경로만 선택한다. configure는 verify-work 호출 후 docs-maintenance로 이어지고, plan-project에서 설계/구성으로 들어갈 수 있다.

## Operations

### O1

선행 입력은 현재 사용자 요청과 기존 도구 계약이다. 네이티브 생성 도구로 등록한 뒤 라우트를 보완하고 최소한의 주변 지도/역할 링크를 갱신한다. 검증은 context 정상/무관 선택, 실제 graph load/구성 진입 gate, Compose canonical 결과, 권한/실패 시나리오와 영향받는 기존 tests다. 서비스 변경이 없어 앱 E2E는 해당하지 않는다.

## Norms

[요청](request.md), [AGENTS](../../../AGENTS.md), [스킬 작성](../../../.agents/skills/maintain-skills/SKILL.md), [보안 경계](../../../.agents/skills/security-review/SKILL.md), [검증](../../../.agents/skills/verify-work/SKILL.md)을 따른다. 작업은 별도 worktree에서 수행하고 main 통합 시 다른 세션의 수정 의도를 보존한다.

## Safeguards

원격 서버는 읽기 전용이다. runtime/build 권한은 스킬의 존재로 생기지 않는다. .env/개인 세션/키를 이미지에 복사하지 않고 Docker socket·privileged를 기본 요구하지 않는다. 전역 prune·임의 volume 삭제·실제 운영 DB 시험을 기본 절차로 넣지 않는다. 네트워크/daemon이 필요 없는 정적 검사를 우선 수행하며, 예제 config 통과를 실제 앱 실행 성공으로 표현하지 않는다. 이전 작업의 완료 증거·현재 main의 다른 세션 변경은 수정하지 않는다.
