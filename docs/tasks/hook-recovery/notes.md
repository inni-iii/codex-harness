# 실패 기록의 에이전트 피드백 연결

2026-11-04 사용자가 “기록 후 에이전트가 다시 쓰는가, 기록만으로 끝나면 소용없다”고 정정했다. 앞선 진단은 writer와 stderr 경로 안내만 있고 자동 소비/해결 추적 연결이 빠졌다. F1: 실패 기록을 다음 도구·재개 맥락으로 전달하는 reader가 없어 현재 에이전트가 놓칠 수 있다. 실제 main의 실패 후 성공 훅에서 additionalContext가 없음을 같은 회귀로 보존한다.

정정 범위에서 미해결 알림→기록 조회→원인 확인→현재 권한의 수정→관련 재검증→task 근거로 해결 표시를 연결한다. 자동 모델/재시도·권한 확대는 추가하지 않는다. 정상에는 제한된 로컬 진단 파일 존재 확인만 추가하고 새 오류일 때 짧은 문맥을 전달한다. UI 변경이 없어 E2E 비적용.

현재 main을 같은 작업용 worktree에 반영하고 .runtime/hook-recovery/baseline.json에 해시를 보존했다. 양쪽 전체 과거 기록 경로를 재검색하고 관련 원문/이전 정정을 재사용했다. 새 메모리/외부 서비스를 기본 의존성으로 추가하지 않는다. 다른 세션 작업을 보존한다.

통합 중 실제 호스트 PostToolUse가 정적 findings와 미해결 additionalContext를 현재 모델에 전달했다(2026-11-04T06:01Z). 안내에 따라 hook status와 doctor를 읽어 타 세션 docker-container-skill의 AGENTS.md artifact 해시와 이번 공통 지침 추가가 충돌함을 확인했다. 타 task 근거를 갱신하지 않고 이번 AGENTS 추가만 제거했다. 소비 절차는 훅의 additionalContext와 기존 verify-work 읽기 경로에 연결되어 요구를 유지한다. 다른 세션 변경과 근거는 그대로 보존한다.

구현 결과: hook_recovery가 세션별 고정 진단(최대7개)을 읽고 다음 성공 도구/SessionStart에 additionalContext를 전달한다. 안정된 동일 실패는 도구마다 중복 주입하지 않는다. hook status는 state 손상 때도 미해결을 읽고, resolve는 현재 실패 해시와 task evidence의 무결성을 확인한다. 실패 자체를 해결 근거로 쓰거나 stale 실패/변조 근거로 해결할 수 없다. 해결 뒤 새 실패는 재개방한다. 기존 deny/정상 출력과 검사 횟수를 유지한다. 코드·CLI·절차 문서·verify-work 소비 경로를 반영했다.

검증: 동일 frozen 회귀 파일 SHA f1a63b1037dad8c756e7ae53b9a03a39a88d48bf9d662bfa22614bb4ce85e4b4의 RED는 Python420 중 F1 1실패/1skip. 관련 검사는1+12+31=44개 전부 통과. main 최종 snapshot은 live_source_changed=false, Python440 중437통과/2실패/1skip, agent-config/secret-patterns 통과. 두 실패와 snapshot doctor 실패는 F2: 다른 세션 docker-container-skill의 RED artifact가 .worktrees 내부를 참조해 source-only 복사에서 빠지는 기존 이식성 결함. FOLLOWUP에 증상·소유 위치·다음 행동을 남겼다. 해당 기록을 임의 수정하거나 failed 보고서를 check 통과 근거로 등록하지 않았다. F1 및 관련 오류·세션 분리·권한 판정·중복·재개·근거 무결성은 실제 테스트 이름/로그에서 통과를 확인했지만, 필수 등록 검사 전체는 실패하므로 task는 needs_revision이다. UI 변경이 없어 E2E 비적용.

실제 main doctor passed, 실제 hook status pending_failures=[] 및 recovery_unavailable=false 확인. 호스트 정적 알림의 모델 맥락 소비와 후속 행동은 실제 관측이고, 콜백 예외/resolve/reopen/resume는 합성 입력을 사용한 실제 main/CLI의 자동 회귀 근거로 구분한다. 독립 평가 없이 자체 검토했다. 정상 비용은 제한된 로컬 읽기, 진단 때만 짧은 맥락이며 별도 모델·자동 재시도·자동 수리 worker는 추가하지 않았다.
