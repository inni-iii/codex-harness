# 프로젝트별 기능 문서 배치와 연결

```json
{
  "version": 1,
  "kind": "reasons-design",
  "profile": "behavioral",
  "requirements": [
    "R1",
    "R2",
    "R3",
    "R4"
  ],
  "operations": [
    {
      "id": "O1",
      "requirements": [
        "R1",
        "R2",
        "R3",
        "R4"
      ],
      "paths": [
        "AGENTS.md",
        "README.md",
        ".agents/context.toml",
        ".agents/skills/docs-maintenance/SKILL.md",
        ".agents/skills/docs-maintenance/references/organization.md",
        ".agents/skills/docs-maintenance/references/navigation.md",
        ".agents/skills/plan-project/SKILL.md",
        ".agents/skills/plan-project/assets/**",
        ".agents/skills/plan-project/references/project-lifecycle.md",
        ".agents/skills/plan-project/references/workflow-setup.md",
        ".agents/skills/plan-project/references/handoff.md",
        ".agents/skills/verify-work/references/acceptance.md",
        "tools/harness/harness/project_documents.py",
        "tools/harness/harness/workflows.py",
        "tools/harness/harness/doctor.py",
        "tools/harness/harness/cli.py",
        "tools/harness/tests/test_project_document_layout.py",
        "tools/harness/tests/test_project_document_links.py",
        "tools/harness/tests/test_workflows.py",
        "tools/harness/tests/test_document_indexes.py",
        "tools/harness/tests/test_layout.py",
        "tools/harness/docs/architecture.md",
        "tools/harness/docs/index.md",
        "tools/harness/docs/project-documents.md",
        "tools/harness/docs/project-workflows.md",
        "tools/harness/docs/workflows.md",
        "tools/harness/docs/verification-audit.md",
        "docs/index.md",
        "docs/README.md",
        "docs/projects/README.md",
        "docs/projects/index.md",
        "docs/tasks/index.md",
        "docs/tasks/project-document-layout/**",
        "docs/tasks/docker-container-skill/task.json",
        "docs/tasks/docker-container-skill/review.json",
        "docs/tasks/docker-container-skill/notes.md"
      ],
      "depends_on": [],
      "verification": "직접/legacy 생성과 배치 반례 RED/GREEN, 문서 저장·중복·선택·실패 보존·경로 경계 및 현재 통합 전체 검사"
    }
  ],
  "decisions": [
    {
      "id": "D1",
      "status": "resolved",
      "operations": [
        "O1"
      ],
      "reason": "사용자가 직접 프로젝트 경로·기능 폴더·기존 정본 갱신/지도와 읽기 자동 연결 구현을 승인했다."
    }
  ]
}
```

## Requirements
R1: 새 프로젝트는 docs/<project>/에 생성하고 예약/legacy 중복·탈출을 차단한다. R2: 같은 기능의 정본을 저장/갱신할 때 파일·인덱스·상위 지도·workflow 조건을 함께 연결한다. R3: feature-folders를 선언한 새 프로젝트의 잘못된 배치/미등록을 검사하고 이전 프로필 읽기는 유지한다. R4: 다른 인덱스 작업·기존 원문/검증 이력·원격/비용 경계를 보존하며 현재 근거로 검증한다.

## Entities
프로젝트 workflow의 documentation.layout=feature-folders가 새 배치 계약이다. 루트의 index/brief/security/README와 공통 architecture/decisions/operations, 기능 features/<feature>가 소유 위치다. task/로그는 기존 docs/tasks와 .runtime에 둔다. 기존 인덱스 검사/조상 선택은 재사용한다. document upsert는 현재 에이전트가 판단한 문서를 소스 파일에서 읽어 정본·지도·선택을 갱신하며 내용의 진위를 자동 판정하지 않는다.

## Approach
생성기/템플릿은 새 경로만 쓰고 doctor는 direct와 legacy를 모두 발견한다. 이전 프로필은 읽기 호환을 두고 새 문서 저장은 canonical 새 프로필에서만 허용한다. 저장은 역할과 경로/topic 조건을 요구하며 관리하는 TOML 블록을 갱신해 반복 호출로 규칙을 중복하지 않는다. 전체 파일 교체/실패 복구·짧은 잠금으로 부분 상태와 다른 writer를 보호한다. legacy migration-plan은 읽기 전용 대응/분류 계획을 제공하고 실제 외부 프로젝트는 주어지지 않아 이동하지 않는다.

## Structure
project_documents 모듈이 배치 검사·문서 저장·이전 계획을 맡고 workflows/doctor/CLI가 호출한다. 새 workflow는 명시 layout을 선언하고 이전 프로필에는 강제하지 않는다. 기존 document_indexes는 그대로 재사용한다. AGENTS/문서 소유/검증/프로젝트 템플릿·현재 사용 안내와 context 패턴을 동기화한다.

## Operations
### O1
기존 생성기/doctor 경계에서 새 경로/배치 반례를 동결해 실패시킨다. 문서 파일·지도·조건을 연결하고 같은 기능의 기존 정본을 갱신한다. 실제 저장→재저장→선택, invalid/경로/잠금/실패, legacy 읽기 및 현재 전체 검사를 확인한다. 기존 완료 MAP이 AGENTS를 참조하는 경우 당시 내용을 immutable runtime 사본으로 보존해 참조/리뷰 서명만 일관되게 옮기고 당시 판정은 유지한다.

## Norms
문서가 필요한지와 어느 기능의 정본인지는 현재 에이전트가 요청/기존 문서에서 판단한다. 도구는 경로·역할·선택 조건·무결성을 연결한다. 문서를 매 구현/검사마다 생성하지 않고 현재 정본을 갱신한다. 기본 project는 draft이며 빈 기능/설계 폴더를 미리 만들지 않는다.

## Safeguards
외부 레포·원격·과거 원본·로그·완료 시각/판정은 임의 수정/삭제하지 않는다. URL/역사적 원문에 전역 문자열 치환을 하지 않는다. 명시적인 새 layout만 엄격 검사하고 legacy 폴더는 읽는다. reserved namespace·경로 탈출/별칭·심볼릭 링크·입력 한도·동시/부분 실패·임의 role/조건을 검사한다. 추가 모델/훅/백그라운드 쓰기나 의미적 자동 승인·제품 E2E 통과를 주장하지 않는다.
