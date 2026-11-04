# 짧은 검증 요청의 기본 계약

2026-11-04 관련 Claude/Codex 전체 기록을 검색 범위로 삼고 관련 비용 정정·기술 평가 및 현재 요청 원문을 읽었다. 이전에 읽은 변경 없는 AGENTS/정본은 재사용했다. Claude 관련 원문 부재·plans 경로 없음/archived JSONL0의 한계는 동일하다.
F1: 절차는 있으나 범위 없는 검증 요청에 적용할 명시적 기본 계약이 없고 verify-work:check가 design/alignment를 선행 요구해 기존 결과물만 검증하려는 진입에서 불필요한 설계 준비를 요구한다. request-only 읽기 검사 진입과 실제 수리의 gate를 구분한다.
네이티브 발견/공통 review 선택/소유 스킬에 연결하고 기존 Stop 미완료 알림을 유지한다. 공식 Hooks UserPromptSubmit은 추가 맥락 주입을 지원하지만 현재 목적에는 추가 훅·프롬프트 수집·신뢰 변경 없이 기존 스킬로 연결한다. UI 변경이 없어 제품 E2E는 비적용이며 선택/절차 시나리오는 확인한다.

구현: verify-work의 description/본문에 짧은 요청을 명시하고 소유 acceptance 참조를 기본 review context와 구현 check 소비에 연결했다. 요청만으로 시작하는 inspect와 필요 시 repair/security/E2E 호출을 추가했다. repair/check의 design/alignment gate는 유지했다. 기본 계약은 대상/현재 제한 복원, 실제 실행·정상/실패·회귀·구조·보안·관련 E2E를 적용 조건에 맞게 선택하고 근거/미확인을 보고한다. 문서/조사에는 제품 E2E를 강제하지 않고 관련 기존 결과를 재사용한다. 새 훅/모델/주기 실행을 추가하지 않았다. 기존 AGENTS의 verify-work 진입을 재사용하고 추가 전역 지침은 만들지 않았다.

검증: 최초 작성 중 flow API 인자 오기를 바로잡고 수정된 같은 테스트 파일로 실제 RED를 다시 보존했다. 등록/행동 수정 전 RED snapshot443개에서 기본 선택/inspect 부재2개 실패를 관측했고 live_source_changed=false였다. RED 원문과 동일 로그는 표준 runtime 경로에 보존해 worktree 의존을 새로 만들지 않았다. 수정 뒤 신규2개, 기존 범위10개, flow31개=43개 관련 검사 모두 통과했다. 실제 기본/문서/UI/auth context·미등록 앱 경로와 request-only inspect/실제 repair/check의 missing route inputs: alignment, design을 별도 GUARD로 확인했다. 적용/제한 시나리오는 작성자의 자체 판단이며 독립 자연어 모델 평가로 주장하지 않는다.

현재 main의 최종 check --full --snapshot --checkpoint final: doctor/agent-config/secret-patterns/Python443 전부 통과, 실패0/기존 환경 skip1, live_source_changed=false. 신규2개는 skip 없이 통과했다. 자체 요구/결함/실패/공유 경계/회귀를 마지막 수정 뒤 재검토했고 새 결함을 찾지 못했다. 독립 평가·실제 제품 E2E·실제 모델 호출은 미수행이다. 명령은 각 checkout 루트의 Python3.14에서 실행했으며 원본/로그는 .runtime/verification-defaults 및 RED/FINAL이 가리키는 보고서에 남겼다.
