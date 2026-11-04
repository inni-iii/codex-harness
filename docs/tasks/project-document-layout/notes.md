# 프로젝트 문서 배치/연결

2026-11-04. 관련 Claude/Codex 전체 접근 경로를 검색 범위로 삼고 현재 직접 경로·기능 폴더·자동 연결 요구와 2026-10-30 선택 읽기 원문을 재사용/추가 확인했다. 관련 Claude 새 원문 부재, plans 경로 없음/archived JSONL0의 한계는 유지한다.
F1: project 생성기와 doctor 프로필 탐색·템플릿이 docs/projects를 전제해 새 직접 경로 계약을 충족하지 못한다. F2: 기존 폴더 지도 검사는 있으나 기능 문서의 배치/읽기 연결 계약과 저장 시 함께 갱신하는 경로가 없어 flat md와 미등록 선택 경로가 생길 수 있다.
같은 세션의 .worktrees/mcp-web-hooks를 재사용한다. 별도 docs-index 세션의 완료된 인덱스 검사/생성/선택 코드는 현재 baseline으로 보존한다. 제품 코드/UI가 없어 E2E 비적용. 실제 서비스 프로필은0개라 외부 프로젝트/기존 서비스 파일을 임의 이동하지 않는다.

2026-11-04 구현/통합: F1/F2를 같은 동결 테스트 파일의 실제 check --snapshot으로 재현했다(458개, 실패2, skip1). 새 직접 경로·명시 layout·doctor 발견/배치 검사·문서 저장/갱신·인덱스/선택 조건 연결을 구현했다. 기능 문서의 broad 종류/전역 바인딩은 거부하고 조건 충돌·심볼릭 링크·예약 이름·입력 한도·잠금·부분 실패 보존을 검사했다. 집중 문서 검사16개, 기존 workflow32개·인덱스8개를 통과했다. 실서비스/UI가 없어 제품 E2E는 비적용이다.
실제 임시 레포 CLI 시나리오: 직접 프로젝트 생성 → login 저장 → 같은 파일 갱신 → 동일 입력 반복 시 docs 해시 불변 → export 추가 → auth 경로에서 최신 login 본문/조상 지도만 선택, export 본문/지도 제외 → doctor 통과. .runtime/project-document-layout/scenario.json과 개별 원본 로그에 명령/cwd/종료 코드를 보존했다.
공통 지침·스킬·템플릿·현재 안내를 동기화했다. 기존 다른 세션의 문서 인덱스 완료 변경과 main drift가 없음을 확인하고 소유 범위만 통합했다. 직접/legacy 프로필을 함께 발견하며 legacy는 읽기 호환·읽기 전용 migration-plan을 유지한다. 실제 서비스 프로필은 없어 외부/기존 서비스 이동은 수행하지 않았다.
AGENTS 변경 전 Docker 완료 MAP 원문을 같은 SHA로 .runtime/docker-container-skill/map-at-completion.md에 보존하고 경로·리뷰 digest/sha를 맞췄다. 해당 작업의 완료 시각·수용 기준·기존 검사/원본은 변경하지 않았다. RED는 원본 report를 그대로 보존하고 results의 log 위치만 동일 바이트 사본으로 옮긴 파생 report와 provenance를 별도 기록했다. 원본 workspace/소스/시각/상태는 보존했다.

최종 통합 검증: check --full --snapshot --checkpoint final 종료0, 등록4개 모두 passed; Python472개 실패0 skip1(격리 runner의 process-group 신호 검사). live_source_changed=false. 동결 RED/GREEN 테스트 SHA 동일. Docker 과거 task는 MAP 위치/review SHA만, review는 evidence digest/위치 보존 주석만 달라졌음을 구조 비교했고 notes와 원문 SHA는 동일하다. 실제 기준 대조·남은 한계는 .runtime/project-document-layout/assessment.json에 보존했다.

완료 근거 확정: 통합 전체 검사를 실제 실행한 원래 source 사본에서 소스/실행 권한/환경이 동일함을 current_sources로 확인하고 유효한 FINAL을 재사용해 evidence verify/complete를 통과했다. 이후 main의 타 세션 작업 기록 변화는 현재 완료의 동작 회귀로 취급하지 않았다. 격리 worktree의 기존 .git 입력 불일치는 harness-connection-recheck F2의 담당 범위이며 해당 코드를 덮어쓰지 않았다.
마지막 StaticCheck 알림 원문/해시와 hook status를 읽었다. 오류2건은 타 세션 document-delivery-defaults의 작성 중 request/design 인덱스 연결이었다. 소유 세션에서 항목을 추가한 뒤 main doctor가 다시 passed이고 hook status의 pending_failures=[]를 확인했다. 내 문서/완료 기록 결함은 없었고, 현재 진단이 없어 hook resolve를 호출할 대상도 없다. 최신 정적 결과는 .runtime/project-document-layout/doctor-after-shared-map.json에 보존했다.
