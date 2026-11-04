# 검사/근거 연결 복구

```json
{
  "version": 1,
  "kind": "reasons-design",
  "profile": "structural",
  "requirements": [
    "R1",
    "R2",
    "R3"
  ],
  "operations": [
    {
      "id": "O1",
      "requirements": [
        "R1",
        "R2",
        "R3"
      ],
      "paths": [
        "tools/harness/harness.toml",
        "tools/harness/tests/test_connection_repairs.py",
        "docs/tasks/docker-container-skill/task.json",
        "docs/tasks/docker-container-skill/review.json",
        "docs/tasks/docker-container-skill/notes.md",
        "docs/tasks/harness-connection-repairs/**",
        "docs/tasks/index.md"
      ],
      "depends_on": [],
      "verification": "등록 전체 계획/미등록 부정 반례, 같은 F1/기존 이식성 회귀의 실제 RED/GREEN, 원본/로그 보존 해시 및 최종 snapshot 전체 검사"
    }
  ],
  "decisions": [
    {
      "id": "D1",
      "status": "resolved",
      "operations": [
        "O1"
      ],
      "reason": "현재 사용자가 진단 F1/F2 수정을 명시했으며 F3 이관은 제외한다."
    }
  ]
}
```

## Requirements
R1: 조사 JSON 두 개만 문서/근거 산출물로 명시 등록해 기존 전체 검사를 실행한다. R2: 완료된 Docker 스킬의 RED 원문·로그·이력을 보존해 worktree 존재에 묶인 근거 경로를 표준 로컬 경로로 옮긴다. R3: 현재 등록 검사/완료 계약과 다른 파일을 보존한다.

## Entities
두 JSON은 기존 조사 결과로 task의 해시에 연결돼 있고 doctor가 엄격 JSON 및 무결성을 읽는다. 실패 보고서와 로그는 당시 상태의 근거이며 현재 통과로 바꿀 수 없다. 기존 완료 task/review는 당시 검토이고 새 이관 manifest는 경로 변경과 원본 해시의 정본이다.

## Approach
harness.toml coverage.documentation에 정확한 두 파일만 추가한다. 원래 RED와 로그를 별도 보존한 뒤 결과 record의 log 경로만 표준 .runtime/checks 보존 위치로 재지정한 파생 보고서를 만든다. workspace/소스/시각/상태/명령/cwd는 그대로 둔다. 기존 RED evidence와 review digest를 일관되게 갱신하며 원래 task/review/RED도 보존한다. 모든 docs JSON을 제외하거나 doctor의 누락 근거 정책을 약화하는 대안은 제외한다.

## Structure
실행기 로직은 변경하지 않는다. 공유 manifest와 completed task/review/notes의 경로만 수정하며 새 테스트는 선택기 반례를 확인한다. 보존 위치는 .runtime/checks 아래이고 이관 manifest/원본 백업은 .runtime/harness-connection-repairs 아래다. 결과는 새 task와 관련 지도에 연결한다.

## Operations
### O1
같은 F1 신규 회귀와 기존 이식성 회귀를 RED로 보존한다. 표준 경로에 원본/로그를 복사하고 해시를 확인한 뒤 파생 보고서 경로와 기존 검토 연결을 갱신한다. 작업 분리 공간에서 수정하고 소유 위치의 현재 해시를 대조해 main에 통합한다. 전체 검사와 새 소스 복사본의 실제 결과를 확인한다.

## Norms
과거 완료 이력은 당시 결과로 유지한다. 이관은 새 검증 실행이나 독립 평가가 아니며 원래 completed_at과 검토 내용을 보존한다. 현재 결과는 새 task의 최종 검사로 판단한다.

## Safeguards
F3의63개는 옮기지 않는다. 원본 worktree/로그는 삭제하지 않는다. report에서 provenance나 결과를 고치지 않고 실제 복사한 log/test_report 경로만 변경한다. 기존 무결성 검사·미등록 파일 차단·회귀 테스트·권한은 낮추지 않는다. UI/E2E·원격·설치·별도 모델은 비적용이다.
