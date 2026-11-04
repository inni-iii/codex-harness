# 연결 누락 두 건 수정

2026-11-04. F1: inventory.json/observations.json이 uncovered여서 전체 검사 시작을 차단. F2: 완료된 Docker 스킬의 RED가 .worktrees 내부를 가리켜 소스 복사본 doctor/이식성2건을 차단. 현재 사용자 승인으로 두 소유 위치의 좁은 수정과 근거 이관을 진행한다. 관련 과거 원문/AGENTS/context를 재검색·확인했으며 이전 조사에서 읽은 변경 없는 원문은 재사용했다. Claude에 관련 새 원문은 발견되지 않았고 plans 경로 부재/archived JSONL0의 한계는 동일하다. UI 변경이 없어 E2E 비적용.

구현: harness.toml에 정확한 inventory.json/observations.json만 documentation으로 명시 등록했다. doctor의 엄격 JSON/기존 task 근거 해시 점검은 유지하고 다른 docs JSON이나 helper.py는 여전히 차단한다. Docker RED 원문 해시는6faf15f8f9baae245556ec4da098e1cf311fefd05f1b5d19fe6c84f2fd1e5d32로 보존했다. 로그3개를 byte-for-byte 복사하고 원본 task/review/보고서를 백업했다. 활성 RED 보고서는 로그 경로3개만 변경했고 시각/workspace/소스/명령/cwd/실패 결과는 보존했다. 기존 완료 검토 판단·contract·completed_at은 유지하고 evidence/review 서명만 현재 참조에 맞췄다. RELOCATION에 원문/변경 manifest를 연결했다.

검증: 격리 worktree에서 RED snapshot Python441 중 F1 1건+기존 이식성2건 실제 실패/skip1. 수정 후 관련1+2개 검사를 모두 통과했다. 원래 Docker worktree의 파일 읽기를 금지한 현재 doctor가 passed였고 보존 원문/로그 해시·기존 contract/리뷰 판단 보존을 확인했다. 소유 파일 현재 해시를 baseline과 비교한 뒤 이번 범위만 main에 반영했다. main 최종 check --full --snapshot --checkpoint final은 live_source_changed=false, doctor/agent-config/secret-patterns/Python441 전부 통과(실패0/skip1). 건너뜀은 기존 process-group signal 차단 subcase이며 신규/이식성 검사는 모두 실행됐다. 같은 F1 테스트 파일과 기존 test_layout 파일의 해시를 RED/FINAL source_snapshot에서 확인해 회귀 근거로 연결했다. FINAL typed check는 실제 전체 등록 검사 보고서를 가리킨다. 모든 명령은 각 레포 루트에서 Python3.14 표준 라이브러리로 실행했다.

최종 자체 검토: 요구·미등록 부정 사례·실패/공유 경계·원문 보존·이식·완료 무결성을 다시 대조했고 새 결함을 찾지 못했다. 독립 평가가 아니며 새 모델·원격·설치·서비스 실행/브라우저 E2E를 추가하지 않았다. F3의 과거63개 근거 이관은 미수행이다. 원본과 현재 로그는 .runtime/harness-connection-repairs 및 FINAL/RED이 참조한 원본 report/log에 보존했다.
