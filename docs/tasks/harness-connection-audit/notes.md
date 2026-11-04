# 하네스 전체 연결 진단

2026-11-04. Claude/Codex의 접근 가능한 전체 기록 경로를 검색 범위로 삼았다. Codex의 2026-10-30 전체 검증 연결 감사 원문(2026-10-22 시작 세션), 2026-10-30 기능 연결 검토 원문(2026-10-20 시작 세션), 2026-11-04 훅 소비 정정 및 현재 원문을 읽었다. Claude 전체 기록/하위 에이전트/메모리도 검색했으나 이 하네스 결정에 관련된 대화는 확인되지 않았다. Claude plans 경로는 없고, Codex archived 경로는 존재하나 접근 가능한 관련 원문은 없었다. 인덱스·history는 탐색 보조로만 썼다. 원문은 읽기 전용으로 확인하며 무관한 내용은 결과에 저장하지 않는다.

첫 context 호출의 --topic 다중값 문법을 repeatable 옵션으로 바로잡아 원문을 읽었다. knowledge search 연결 검색 결과는0건이며 적용되는 기존 채택 규칙의 실제 context 소비와 근거 해시도 확인했다. UI 변경이 없어 앱 E2E 비적용이다. 세션/전역 설정과 다른 작업은 수정하지 않는다.

F1(검사 등록 연결 누락): check --full --plan에서 docs/tasks/docker-infra-survey/inventory.json·observations.json이 uncovered_paths로 남아 needs_configuration을 반환한다. doctor/agent-config 통과로 이 연결 부족을 해결했다고 하지 않는다. 검사 선택기는 의도대로 차단하지만 두 조사 산출물의 등록 연결은 빠져 있다. PLAN 원본에 보존하며 향후 등록은 해당 두 산출물의 책임/검사 방식을 명시해 좁게 처리해야 한다.

F2(작업 근거의 이식 경로): 완료된 docker-container-skill의 RED artifact가 .worktrees/docker-containers/.runtime 내부 보고서를 참조한다. 현재 원본은 있으나 source-only 복사에는 없어 doctor 실패를 재현했다. 기존 전체 Python440 검사 중2개 이식성 실패와 같은 원인이다. 이번에는 새 임시 source-only 사본에서 doctor를 실행해 동일 오류/exit2를 독립 재현하고 사본을 정리했다. 소유 task/증거는 변경하지 않았다.

정상 경로:15개 스킬의 실제 context --read 선택과 파일 읽기,36개 flow 노드와 허용 edge,156개 Markdown의654개 로컬 링크/앵커 후보,173개 CLI 예제의 실제 argparse 인자 계약을 확인했다. 깨진 파일 링크·앵커 후보·인자 오류는 없었다. Markdown 그래프에 직접 연결되지 않은 결과 문서도 task/evidence 참조를 더하면 모두 찾을 수 있었다.

OpenAI Docs/Svelte는 현재 host 도구에서 실제 목록 응답을 받았다. 로컬 mcp-check는 양쪽 unavailable이지만 socket.getaddrinfo도 gaierror(errno8)여서 로컬 DNS 제약과 구분한다. 서비스/MCP 자체 장애로 단정하지 않는다. 현재 Codex CLI0.166.0의 두 기본 MCP enabled도 확인했지만 인증unknown만으로 성공/실패 판정하지 않았다.

F3(과거 근거 이관 연결 누락):11개 작업의63개 .runtime 증거가 현재 경로에는 없다(완료10개 작업59개, 진행 중1개 작업4개). 이전 로컬 레포와 현재 두 worktree에서 동일 상대경로/등록 SHA-256을 대조했고63개 모두 이전 레포의 원본에서 일치했다. 삭제/소실로 단정하지 않는다. 복구 위치는 공유 소스에 개인 경로를 넣지 않고 .runtime/harness-connection-audit/recovery-locations.json에만 남겼다. 이관하더라도 과거 시점 결과이지 현재 소스 검증을 의미하지 않는다. 소유 기록/원본은 읽기 전용으로 보존했다.

기존 전체 검사 원본은33개 테스트 모듈/440개이며 현재 실행/테스트/설정 파일의 신규·해시 변경이0개여서 유효한 범위만 재사용했다. 결과는437통과/2실패/1skip이고 실패 둘은 F2다. 새 evaluate-pilot은 네트워크/모델/브라우저 없이 실제 CLI 실행기·증거·검토·완료·실험 비교를6개 합성 사례로 확인했으며6/6 통과했다. 서비스/독립 에이전트 품질의 증거로 확대하지 않는다. 추가 새 결함이 없는지 반대 경로·미등록 경로·read-only consumer를 대조했고 F1/F2/F3의 수정은 현재 조사 범위 밖 후속으로 연결한다.

최종 문서 추가 뒤159개 Markdown·659개 로컬 링크/앵커 후보와173개 CLI 예제 인자 계약에서 오류0개. 현재 문서 범위의 등록 doctor/secret-patterns가 실제 통과했다. 첫 정적 관측 파일을 후속 실행이 덮어쓴 것은 원래 관측 내용으로 복원하고 등록 SHA-256 일치로 확인했으며 최종 관측은 별도 파일로 보존했다. F1-F3는 발견/분류 완료이고 수정·이관은 미수행이다.
