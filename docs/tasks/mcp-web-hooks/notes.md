# MCP·웹검색 호출 경계 보강

2026-11-04 현재 사용자 요청에 따라 연결된 MCP에 일반 훅 처리와 내장 웹검색 전후 검증 절차를 추가한다. 이전의 Python Expat 복구 기록과 변경은 보존한다. 현재 메인 소스의 해시를 .runtime/mcp-web-hooks/baseline.json에 기록하고 detached worktree에서 수행한다.

현재 MCP 필터 누락은 이전 정의의 범위였으며 확인된 코드 결함으로 꾸미지 않는다. 새 요구는 MCP 호출 전 권한/인자 안내, 응답 오류 확인과 비신뢰 응답 검토 안내, MCP의 로컬 설정 변경 후 기존 정적 점검이다. 셸 명령 파서에 MCP 인자를 보내지 않는다. 내장 웹검색은 공식적으로 Pre/Post 도구 훅이 없으며 에이전트의 명시적인 전후 절차로 연결한다. 자동 내용 검증/차단/새 검색 MCP 설치는 하지 않는다.

검증 범위: 새 MCP 정상/오류/누락/공격 문자열/동시 콜백·기존 셸 경계, 실제 stdin, context 선택과 웹검색 절차의 정상/빈 결과/충돌/민감 검색어 시나리오, 최종 등록 검사. 브라우저 UI 변경이 없어 E2E 비적용. Claude·Codex 전체 기록 경로를 재검색해 관련 원문과 날짜를 확인했고 앞서 읽은 동일 원문을 재사용했다. Claude plans와 Codex 보관 JSONL은 없었다.

구현 후 집중25개 통과. 변경 전 새 수용 사례는 .runtime/mcp-web-hooks/before.log에서 실패했고 기존19개는 유지됐다. 이는 새 기능의 이전 상태 차이이며 기존 정의를 계약 위반으로 꾸미지 않았다. MCP 오류와 정적 findings의 동시 알림 보존 사례를 추가해 확인했다. 세 context 주제 선택과 공식 Tool coverage 원문 대조를 수행했다.

격리된 snapshot 등록 검사 전체 passed: Python413개 실행·실패0·기존 환경 제한skip1, live_source_changed=false. doctor·agent-config·secret-patterns도 통과했다. root 반영 시 시작한 baseline SHA와 현재 main을 대조해 이번14개 경로 델타만 적용하고 Expat 복구 작업은 보존한다. 새 Pre/Post 정의의 실제 호스트 신뢰는 자동 설정하지 않는다.

메인 반영 전 모든 변경 경로의 baseline·검사 당시 소스 해시를 대조했다. 반영 보조 스크립트가 처음 요약 보고서에서 해시를 찾다가 쓰기 전 중단됐고, 원본 보고서 경로로 보완한 뒤14개 경로를 반영했다. 기존 Expat 복구 문서와 사용자 변경은 유지했다. .runtime/mcp-web-hooks/integration.json에 경로별 전후 SHA를 남겼다.

메인 최종 보고서 .runtime/checks/45d64d84ad344a4c9adeb9b34e00307b/report.json: passed, Python413개 실행·실패0·기존 환경skip1, doctor/agent-config/secret-patterns 통과. 검토 범위의 새로운 계약 위반은 없었으며 자체 검토로 기록했다. evidence/flow의 실제 근거를 연결했고 새 정의의 신뢰 검토 전 네이티브 자동 발생은 미확인으로 남긴다.
