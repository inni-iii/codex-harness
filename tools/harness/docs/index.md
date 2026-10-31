# 하네스 문서 지도

[전체 문서 인덱스](../../../docs/index.md)에서 이 하네스가 필요한 경우에만 읽는다.
한 행의 질문에 맞는 현재 원문부터 읽고, 배경·과거 기록은 그 근거가 필요할 때 연다.

## 현재 작업에 쓰는 안내

| 질문·상황 | 정본 | 읽을 조건 |
|---|---|---|
| 처음 설치·MCP/브라우저 준비 | [설치와 도구](tools.md) | 새 환경·연결 점검 |
| 패키지 관리자·고정 의존성 설치 | [환경 준비](environment.md) | manifest/lock·지원 범위 |
| 하네스 폴더·책임·구현 경계 | [구조](architecture.md) | 모듈·파일 위치 파악 |
| 모델 추천 설정·목록·정책 | [추천기 사용법](usage.md) | catalog/route 구성 |
| 선택한 모델로 작업 수행 | [실행 안내](execution.md) | run/chat·인수인계·실패 처리 |
| 새 프로젝트와 문서/검사 연결 | [프로젝트 워크플로](project-workflows.md) | project 생성·context 규칙·검사·보안 범위 |
| 목표·마일스톤에서 다음 작업 선택 | [프로젝트 진행](../../../.agents/skills/plan-project/references/project-lifecycle.md) | 요구·성공 조건·갭의 전후 평가·bottom-up 발견·계획 정본 |
| 작업 생성·진행·인수인계 | [작업 흐름](workflows.md) | task/notes·연구/구현 연결 |
| 코드 전 의도·경계·REASONS·설계/정렬 준비 | [설계와 구현 진입](reasons.md) | 분석/설계/정렬·typed 근거·작은 수정·변경 분류 |
| 스킬 라우트·call/return·조건부 전이·재진입 | [스킬 흐름](skill-flows.md) | 여러 스킬을 잇는 작업·검증 실패·사용자 선택 대기 |
| 작업의 완료와 근거 연결 | [완료 계약](completion.md) | evidence/review·종류별 완료 |
| 현재 task 연결·중단 재개·자동 정적 점검 | [생명주기 훅](hooks.md) | hook bind/status/clear·이벤트·신뢰·원격 쓰기 보조 차단의 한계 |
| 한 요청에서 검토·보완·회귀 | [검토 라운드](review-rounds.md) | 실제 발견·수정 전/후·재검토 |
| 영향받는 검사·실행·결과 판정 | [검증 사용법](verification.md) | check/계획·범위·실행 |
| 결과 재사용·과거/현재 근거 구분 | [검증 무결성](verification-integrity.md) | 캐시·stale·증거 계약 |
| 공통 스모크·E2E 시점·전체 연결 | [검증 연결 감사](verification-audit.md) | 검사 확대·자동화 한계 |
| 보안 점검·비밀값·advisory/config | [보안 도구](security.md) | 허용 범위·검사 결과의 의미 |
| 여러 세션 격리·변경 통합 | [세션과 통합](sessions.md) | worktree·고정 사본·합친 결과 |
| 실제 실험 실행·집계·비교 | [실험 도구](experiments.md) | 프로토콜·입력·지표·예산 |
| 하네스 사례 평가·평가 한계 | [평가 범위](harness-evaluation.md) | 파일럿·대표 사례·성능 주장 구분 |
| 학습·교훈의 검토·검색·공유 | [지식 관리](knowledge.md) | candidate/adopted·scope·근거 |
| 스킬 작성·등록·검증 | [스킬 관리](skill-authoring.md) | 기존 스킬 보완·새 절차 생성 |

## 설계 배경·선별 근거·과거 기록

현재 명령은 위 사용법과 실제 구현으로 확인한다. 아래 초안·관측 기록을 현재 계약이나 새 실행 권한으로 취급하지 않는다.

| 자료 | 상태·읽을 조건 |
|---|---|
| [추천기 계약](contracts.md) | 계약 설명·초안 표기를 확인하며 실제 입출력과 대조할 때 |
| [추천기 설계](design.md) | 초기 설계 의도·가정이 필요한 때; 현재 실행 안내와 구분 |
| [레포 구성안](repository-setup.md) | 초기 구성 제안·미결정의 배경 확인 |
| [공통 작업 규격](task-workflow.md) | 공통 절차 초안과 현재 구현의 차이 확인 |
| [스킬 선별 이력](skill-sources.md) | 채택·제외·당시 스킬 수·원문 범위 확인 |
| [SPDD·REASONS 보완 조사](spdd-reasons-research.md) | 2026-10-31 당시 조사·반영 제안; 현재 계약은 설계와 구현 진입 안내에서 확인 |
| [문서 스킬 도입 조사](docs-maintenance-research.md) | docs/wiki 공개 사례·채택 근거·확인 한계 |
| [보안 재점검 기록](security-recheck-2026-10-31.md) | 해당 날짜의 재현·수정·미검증 조건 확인 |
| [CLI 기능 관측](cli-capabilities.md) | 관측한 CLI 기능/버전을 확인; 현재 지원은 재검증 |
| [외부 참고 자료](references.md) | 관련 외부 원문을 찾아야 할 때 |

## 지도에 없거나 오래된 경우

먼저 이 폴더에서 관련 제목·명령·심볼을 검색한 뒤 후보 원문을 연다. 인덱스 누락을 문서 부재로 단정하지 않는다.
새 문서·제목/경로·상태 변경은 해당 행을 함께 갱신한다. 로그·검사 결과 전문이나 문서 본문을 이곳에 붙이지 않는다.
