# 반복 작업 비용 보완

```json
{"version": 1, "kind": "reasons-design", "profile": "behavioral", "requirements": ["R1", "R2", "R3", "R4"], "operations": [{"id": "O1", "requirements": ["R1", "R2", "R3", "R4"], "paths": ["AGENTS.md", ".agents/skills/research/SKILL.md", ".agents/skills/research/references/retrieval.md", ".agents/skills/verify-work/references/checkpoints.md", ".agents/skills/maintain-skills/SKILL.md", "tools/harness/harness/evidence.py", "tools/harness/harness/evidence_records.py", "tools/harness/harness/task_timing.py", "tools/harness/harness/cli.py", "tools/harness/tests/test_work_efficiency.py", "tools/harness/docs/completion.md", "tools/harness/docs/workflows.md", "tools/harness/docs/architecture.md", "docs/tasks/harness-work-efficiency/**"], "depends_on": [], "verification": "묶음 등록의 정상/부분실패/중복·잘못된 경로·기존 리뷰 보존/미완료 판정·시간 합계/중복 보고서·관련 회귀와 최종 등록 검사"}], "decisions": []}
```

## Requirements

R1 이미 확인한 원문/명령은 변경분만 추가 확인하고 조사 종료 조건·문서 정본과 관련 검사→통합 후 최종 검사를 연결한다. R2 여러 증거를 한 번에 검증해 원자적으로 등록한다. R3 기존 리뷰를 보존하며 현재 계약/증거 ID·실행 사실만 준비하고 판단은 pending으로 남긴다. R4 단계별 경과를 표시하고 검사 실행 합계와 구분한다.

## Entities

현재 task 계약·기준별 method·증거 파일/해시/원본 날짜·검사 보고서·검토 초안/판정·작업 시계와 단계 전환. 기존 공개 add/verify/complete 계약을 보존한다.

## Approach

기존 evidence.verify_entry와 로컬 경로/JSON 검증을 재사용한다. import는 엄격한 manifest를 메모리에서 모두 준비한 뒤 한 번만 task를 저장한다. 리뷰 초안은 새 출력 경로를 허용하고 자동 통과/서명/종료를 하지 않는다. timing은 로컬 명시 mark로만 측정해 과거 세션을 자동 추측하지 않는다.

## Structure

evidence_records는 묶음 입력과 관측 요약, 기존 evidence는 추가/완료의 정본, task_timing은 runtime 단계 시간, cli는 인자 연결. 운영 규칙은 기존 스킬/AGENTS의 해당 위치만 보완한다. 새 스킬·설치·원격 쓰기는 없다.

## Operations

### O1

 현재 승인 범위·관련 과거 원문과 기존 구현을 확인했다. 이 설계와 정렬을 연결한 뒤 보조 명령·기존 운영 지침을 수정하고 정상/거부/부분 실패·새 리뷰/시간 사례를 실행한다. 격리 공간은 관련 검사만 수행하고 해시 대조로 통합 후 전체 검사 한 번을 수행한다.

## Norms

양쪽 전체 과거 기록 검색 범위·관련 원문 확인, 원본/타 세션 변경, 문서 지도와 필수 보안/완료 조건을 유지한다. 동일 원문의 재출력과 단순 지표/로그 복사를 줄이며 의미 판단·실제 근거 대조는 유지한다.

## Safeguards

비정상 manifest/중복ID/경로 탈출/변조/부족한 method는 부분 등록하지 않는다. 기존 리뷰를 덮어쓰지 않고 새 초안은 reviewer 빈 값·판정 pending·independent false로 남긴다. 시간 보고는 기록 전 구간을 unclassified로 표시하며 병행 실행 합계를 wall time으로 바꾸지 않는다. 로컬 single-writer/낙관적 충돌 검사이며 OS sandbox·분석의 진실성을 자동 승인하지 않는다.

