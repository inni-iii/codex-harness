# 현재 연결 재점검과 공유 경계 보완

```json
{"version": 1, "kind": "reasons-design", "profile": "behavioral", "requirements": ["R1", "R2", "R3"], "operations": [{"id": "O1", "requirements": ["R1", "R2", "R3"], "paths": ["tools/harness/harness/document_indexes.py", "tools/harness/harness/core.py", "tools/harness/tests/test_connection_recheck.py", "docs/tasks/harness-connection-recheck/**", "tools/harness/tests/test_lifecycle_hooks.py"], "depends_on": [], "verification": "동일 회귀 파일의 실패 전/후·동시 문서 작성자 보호·소스/메타데이터 구분·현재 연결 행렬·등록 전체 검사와 합성 pilot"}], "decisions": []}
```

## Requirements

R1 동시 task/project 지도 갱신에서 항목과 사용자 본문을 보존한다. R2 Git worktree 포인터는 검증 소스로 취급하지 않고 실제 소스 변경은 계속 검출한다. R3 기존 지침/스킬/flow/CLI/검사/완료 연결과 다른 세션의 새 문서 배치를 현재 근거로 대조한다.

## Entities

폴더 지도·부모 지도, 독립적인 생성 작업, 문서 작성자 잠금, 임시 파일/원자 교체, 실제 소스 목록, Git 메타데이터와 typed 증거.

## Approach

지도 갱신을 같은 레포 문서 작성자 잠금으로 직렬화하고 같은 폴더의 임시 파일을 원자 교체한다. project_documents의 기존 document-write.lock과 잠금 위치/권한 경계를 공유해 서로 덮어쓰지 않는다. Git 메타데이터 파일은 디렉터리와 같이 소스 순회에서 제외한다.

## Structure

document_indexes.py 안에 지도 갱신 보호를 둔다. core.files는 .git 포인터 파일을 yield하지 않는다. 다른 세션의 project_documents·workflows·CLI·문서 계약은 수정하지 않고 실제 통합 상태를 검증한다.

## Operations

### O1
현재 RED 476개 중 이번 반례4건을 관측했다. 잠금·원자 교체와 .git 파일 제외를 구현하고 동일 파일의 GREEN을 확인한다. 현재 연결 행렬·6종 pilot·전체 검사에서 다른 세션 변경과 미확인을 구분한다.

## Norms

원격 읽기 전용·설치/추가 모델/실서비스 실행 미수행. 다른 세션의 승인된 docs/<프로젝트> 구조와 인덱스 우선 읽기를 보존한다. 과거 보고서의 내용·해시·완료 시각을 현재 결과로 바꾸지 않는다.

## Safeguards

기존 잠금을 자동 삭제하지 않고 제한 시간 뒤 명확히 실패한다. 예외 시 자기 임시 파일과 자기 잠금만 정리하고 기존 지도 내용은 유지한다. symlink/runtime 경로 보호·추적된 소스/생성물 구분과 실제 소스 변경 검출은 약화하지 않는다. 검사통과를 서비스 품질/외부 연결/자연어 스킬 판단의 보증으로 확대하지 않는다.

문서 잠금이 만든 빈 runtime 폴더 때문에 기존 심볼릭 링크 보안 테스트가 준비 단계에서 실패했다. 빈 폴더만 제거해 악성 runtime 링크 fixture를 정확히 구성하고, 외부 쓰기 거부 assertion은 그대로 유지한다.
