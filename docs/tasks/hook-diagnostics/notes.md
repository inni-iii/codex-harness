# 훅 실패 진단 보강

2026-11-04 현재 사용자 승인: 향후 기능 구현 비용을 크게 늘리지 않는 조건으로 진단을 보강한다. 기존 검사·모델 호출을 추가하지 않고 정상 출력은 유지한다. Python·보안·검증 스킬과 최소 관측 참조를 적용한다. 앱 UI 변경이 없어 브라우저 E2E 비적용.

과거 Claude·Codex 전체 접근 가능 경로를 재검색했고 같은 대화에서 읽은 원문을 재사용했다. 2026-10-30 Codex 원문에서 단계/시간 중심 관측 원칙을 확인했다. 현재 예외 요약이 원인을 구분하지 못하는 것은 새 요구의 보강 대상으로 다루며 기존 계약 위반으로 꾸미지 않는다. Claude plans 및 Codex 보관 JSONL은 앞선 확인 범위에 없었다.

같은 세션의 기존 detached worktree를 재사용하고 메인267개 이상 소스의 현재 SHA를 .runtime/hook-diagnostics/baseline.json에 기록했다. 다른 세션의 docs/tasks/docker-infra-survey는 보존한다.

집중 검사31개와 실제 stdin 성공/상태 JSON 오류의 단계·코드·0600 기록·비전파를 확인했다. 이후 doctor가 다른 세션 Docker 조사 보고서의 inventory.json 링크로 실패했다. 사본은 복사 시점의 in_progress 상태였고 메인에는 해당 파일·완료 기록이 생긴 상태임을 읽기 전용으로 대조했다. 해당 완료 폴더만 사본에 갱신하고 변경 baseline을 baseline-refresh.json에 보존했다. Docker 조사 내용을 수정하거나 검사를 제외하지 않았다.

코드·관련 검사·정본·작업 지도와 이 task의7개 경로 델타만 메인에 반영했다. 시작 baseline과 현재 main을 대조했고 현재 Docker 완료 기록 및 이전 Expat/MCP 변경을 보존했다. 메인 최종 등록 검사로 공유 소비자 회귀를 확인한다. 새 모델 호출·검사 주기·성공 출력 변경은 없다.

메인 --snapshot --full은 다른 세션의 inventory.json·observations.json 검사 범위 미등록으로 needs_configuration이고 실행된 검사는0개였다. 이는 통과로 기록하지 않는다. 현재 doctor는 통과한다. 다른 작업의 기록/검사 정책은 수정하지 않고 이번7개 변경 경로를 명시해 관련 등록 검사(기존 Python 전체 회귀 포함)를 수행한다. 사유와 원본 선택 결과는 full-scope-limit.md/json에 보존한다.

최종 관련 snapshot 검사: .runtime/check-snapshots/c63c446800114a40bf72f8733a8814eb/checks/ce039b837f354c90b0f98a324e76ebe5/report.json, passed·live_source_changed=false. Python419개 실행·실패0·기존 환경skip1, doctor/secret-patterns 통과. 전체 레포 등록이 완료됐다는 주장은 하지 않는다. 현재 세션 정적 hook-checks에서도 elapsed_ms·reason_codes를 실제로 확인했다. 정상 호출의 출력·검사 수 보존과 새 실패 파일 없음, 비밀 원문 비전파를 자체 검토했다.
