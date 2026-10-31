# REASONS 설계·정렬과 구현 진입 조건

2026-10-31. 사용자 승인: SPDD 조사안의 기존14개 스킬 통합·설계 전 의도/경계·typed 설계/정렬 근거·docs 변경 분류/동기화·선택 읽기를 구현한다. 관련 양쪽 과거 기록/정정과 조사 원문을 재사용하고 새 기록을 확인했다.

## 설계와 검증 계획

Markdown 설계 정본의 첫 JSON fence에 제한된 REASONS 식별/프로필·R/O/범위/선행 작업·결정 메타데이터를 둔다.7관점 본문과 기계 연결은 한 파일에서 관리하며 별도 상태 장부를 만들지 않는다. alignment artifact는 현재 설계 SHA·task 계약·선택 O·수용 기준·실제 결정 근거·검토자를 묶는다. 형식 검사가 의미적 합의를 보증하지는 않는다.
공통 frame 생성에서 활성 준비 검사를 호출해 start/move/call/restart를 모두 다루고, 재개/판정에서도 입력을 재확인한다. 기존 call/transition/3조건·실패 맥락·task/evidence를 재사용한다. plan의 분석/설계/정렬, docs의 요구 변경/구현 설명 동기화 경로를 추가한다.
격리 사본과 파일별 기준 SHA로 기존 미커밋 변경을 보존한다. 정상/누락/무관한 artifact·낡은 계약/검토·범위/의존/선택 작업의 미결정·현재 승인 재사용·경량 수정·재진입·선택 읽기·이전 기록·CLI·기존 회귀를 확인한다. 최종 통합 검사를 수행한다. 제품 UI가 없어 앱 브라우저 E2E는 수행하지 않는다.

## 실제 초안 결함과 회귀

R1: selected Operations에 선행 작업이 포함되기만 하면 실행 순서가 거꾸로여도 준비로 인정했다. 실제 test_selected_dependencies_must_be_in_executable_order가 실패했다. 선택 순서에서 선행 O가 앞서야 함을 검사한다.
R2: 선택 읽기의 정규식이 선택 O의 코드 fence 안에 있는 ### O2 같은 예시를 진짜 작업 경계로 취급해 필요한 예시를 잘라낼 수 있었다. fenced 예시 보존과 무관한 실제 O 본문 제외를 같은 회귀로 확인한다. 헤딩 추출과 선택 읽기 모두 fence를 인식하도록 보완한다.
이번 격리 초안에서 확인한 결함이며 이전 완료 구현의 결함으로 보고하지 않는다. 같은 회귀 파일/소스를 보존한 RED 보고서에서 재현 후 수정한다.

R3: 정렬 JSON이 basis/dependency를 ID로만 참조하면 현재 task entry를 유효한 다른 파일로 재지정했을 때 검토 당시의 결정 근거와 달라져도 감지하지 못했다. 검토가 참조하는 evidence entry 서명을 함께 묶어 재개 때 대조한다.
검토 근거 서명 필드를 추가하면서 공통 fixture의 입력 형식이 강화된다. R1/R2 원본28사례 RED는 그대로 보존하고, 동일 행동/기대값의 안정된 회귀3사례 파일을 추가한 별도 원래 초안 사본에서도 실제 실패를 확인한다. GREEN은 같은 회귀 파일 SHA를 사용한다. 공통 fixture의 새 필드 추가를 테스트 약화나 이전 원본 동일 주장으로 숨기지 않는다.

## 반영 결과와 실제 검증

기존14개 스킬을 유지하며32개 라우트/93개 경로로 확장했다. Markdown 정본+작은 JSON metadata, pending 정렬 양식/ready CLI, 제한된 entry_checks/result_checks·typed 설계/검토·선택 읽기를 구현했다. 현재 code routes와 verify-work:check의 진입에는 design/alignment를 요구하고 call/transition에서 유효한 동일 이름 입력을 상속한다. 새 implement/debug 스킬도 기본 준비 입력을 요구한다.
plan-project의 분석/설계/정렬, docs의 요구 변경/구현 설명 동기화·원문 권위·R/O/검토/검사·wiki/index 연결을 구현했다. 기존 결정이 충분하면 승인 질문 없이 진행하고 editorial/exploratory는 이유가 있는 경량 계약을 사용할 수 있다. 형식·범위 검사가 실제 의미/사용자 신원이나 API 밖 OS 쓰기 차단을 보장하지는 않는다.

격리 새34개 사례와 기존flow31개/skill 생성3개가 통과했다. 새 합성 기능 fixture는 설계 전 Python 코드가 없는 상태에서 진입 거부→설계/정렬/현재 계약 읽기→실제 코드 작성→소유자/비소유자/누락3행동검사→검증 call/return→문서/인덱스 종료를 수행했다. 작성한 known-answer fixture이며 실제 제품/독립 평가가 아니다.
현재 폴더에는 기준 SHA와 대조해41개 파일을 반영했고 관련 task/문서 지도·현재 설계 근거를 추가했다. 최종 통합 snapshot은 doctor/agent-config/secret-patterns/python 모두 통과했다.407개 테스트, 실패0·환경skip1, live_source_changed=false, 미룬 검사 없음이다. skip은 sandbox 그룹 신호 하위 사례이고 이번 새 회귀는 모두 실행됐다. 스킬14개는 레포 검증과 기존 cached PyYAML을 읽기 전용으로 사용한 skill-creator 검증을 통과했다. 설치/전역 설정 변경 없음.

이번 작업 자체는 새 검사기를 만드는 bootstrap이다. 구현 전 사용자가 승인한 연구안·초기 설계/범위 notes를 기준으로 격리 공간에서 만들고 통합 후 동일 범위를 현재 Markdown/정렬 형식에 묶었다. 새 정렬→maintain-skills→verify-work 호출/복귀→docs sync/validation 호출/복귀→index에서 finished, revision33, stack0을 확인했다. 코드/문서와 실제 검사 근거를 재사용했고 새 빈 위키/자동 지식 채택이나 사용자 재승인을 추가하지 않았다.

근거는 REQUEST(현재 요청/범위), DESIGN(정본), ALIGN(현재 설계/작업/결정 근거 서명), OWN(통합 파일 SHA), TARGET(새34개), RED(동일 안정3사례의 실제 실패), GREEN(통합407개), CONTEXT(필수 원문과 현재 설계/선택 O), SELF(새 실제 흐름)에 연결했다. 최초28개 실패/소스도 별도로 보존했다. 최종 리뷰는 작성자 자체 검토이며 독립성을 꾸미지 않는다. 기존 변경·과거 완료 이력·별도 worktree·원격 서버·커밋/푸시를 변경하지 않았다.
