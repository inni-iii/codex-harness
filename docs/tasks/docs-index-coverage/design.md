# 문서 인덱스 완전성과 선택 읽기

```json
{"version": 1, "kind": "reasons-design", "profile": "behavioral", "requirements": ["R1", "R2", "R3", "R4"], "operations": [{"id": "O1", "requirements": ["R1", "R2", "R3", "R4"], "paths": ["tools/harness/harness/document_indexes.py", "tools/harness/harness/doctor.py", "tools/harness/harness/context.py", "tools/harness/harness/tasks.py", "tools/harness/harness/workflows.py", "tools/harness/tests/test_document_indexes.py", "tools/harness/tests/test_document_index_contract.py", "docs/**/index.md", "tools/harness/docs/index.md", "docs/tasks/docs-index-coverage/**", ".agents/skills/docs-maintenance/references/navigation.md", ".agents/skills/plan-project/references/workflow-setup.md", ".agents/skills/plan-project/references/handoff.md", ".agents/skills/setup-environment/SKILL.md", "AGENTS.md", "docs/index.md", "docs/README.md", "tools/harness/docs/**", ".agents/skills/docs-maintenance/references/validation.md", ".agents/skills/plan-project/assets/project-index.md.tmpl"], "depends_on": [], "verification": "동일 회귀의 RED/GREEN, 실제 폴더 감사, 선택 읽기와 생성기, doctor 및 관련 전체 검사"}], "decisions": []}
```

## Requirements

R1 문서 루트 docs/와 tools/harness/docs/의 각 폴더에 index.md를 둔다. R2 바로 아래 Markdown 파일의 링크와 역할 설명 및 하위 폴더 index 링크를 검사한다. R3 project/task 생성과 관련 인덱스 우선 읽기를 연결한다. R4 무관한 본문을 모델에 전달하지 않고 실제 누락/이동/코드예제/경로 경계 회귀를 보존한다.

## Entities

문서 루트, 폴더별 index.md, 직계 Markdown 문서, 직계 하위 폴더 지도, 기존 task/evidence. 실행 로그와 개인 대화는 문서 루트 밖에 유지한다.

## Approach

doctor에서 파일 목록과 인덱스만 대조하는 표준 라이브러리 검사기를 호출한다. 모델은 작은 지도를 따라 필요한 본문만 읽는다. 모든 파일에 빈 설명을 자동 채우거나 전체 문서를 context에 적재하지 않는다.

## Structure

document_indexes.py가 지도 검사·부모 지도 연결·관련 지도 경로를 소유한다. doctor가 실패를 보고하고 tasks/workflows 생성기가 새 지도를 연결한다. context는 선택된 문서의 실제 조상 지도만 추가한다. 기존 필수·보안 문서와 레거시 명시 읽기는 보존한다.

## Operations

### O1
누락 회귀를 먼저 실행하고 검사·생성·선택 경계를 보완한다. 기존 Markdown 본문·완료 이력은 보존하고 역할/조건 중심의 새 지도 및 필요한 진입 링크만 추가한다. 현재 폴더 전체를 감사하고 관련 회귀 및 등록 검사를 수행한다.

## Norms

사용자의 2026-11-04 필수 인덱스 요구와 2026-10-30 인덱스 우선·선택 읽기 결정을 따른다. 다른 세션의 내용은 상태를 바꾸지 않고 지도에서만 참조한다. 추가 설치·외부 모델·원격 실행·자동 커밋은 없다.

## Safeguards

파일 링크와 별도 설명의 존재는 검사하지만 내용의 의미적 정확성을 자동 보장하지 않는다. 코드예제/주석 안의 가짜 링크는 항목으로 인정하지 않는다. symlink·경로 탈출은 거부하며 파일 본문은 검사기가 읽지 않는다. 링크 전체를 재귀로 context에 펼치지 않는다. 미확인은 사실대로 남긴다.
