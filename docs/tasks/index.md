# 작업 기록 지도

목표에 맞는 작업만 선택해 task.json의 현재 상태·수용 기준·근거를 읽고, 재개/실패 맥락이 필요하면 notes.md를 읽는다.
아래는 탐색용 요약이다. 다른 세션의 진행 상태를 별도 복제하지 않는다.

| 작업 지도 | 역할·읽을 때 |
|---|---|
| [docker-container-skill](docker-container-skill/index.md) | 다른 프로젝트의 Dockerfile·Compose·실행 환경을 설계·구성·진단·검증하는 재사용 Docker 스킬을 만들고 하네스의 선택·flow·문서에 연결한다 |
| [docker-infra-survey](docker-infra-survey/index.md) | 이 노트북의 접근 가능한 저장소와 Docker 실행 환경을 읽기 전용으로 조사하고 범용 하네스의 컨테이너 인프라 구성안을 근거와 함께 보고한다 |
| [docs-index-coverage](docs-index-coverage/index.md) | 문서 폴더별 index와 역할 설명을 검사하고 인덱스부터 필요한 문서만 읽는다 |
| [docs-index-review](docs-index-review/index.md) | 문서 인덱스 우선 탐색과 주제부터 설계·순차 구현까지의 연결을 보완한다 |
| [docs-maintenance](docs-maintenance/index.md) | 공개 docs·LLM Wiki 사례를 조사해 프로젝트 문서 관리 스킬과 선택 연결을 만들고 검증한다 |
| [harness-capabilities](harness-capabilities/index.md) | 검토 지식·스킬 관리·환경 준비·Codex 설정 감사의 레포 내 보강 |
| [harness-capabilities-audit](harness-capabilities-audit/index.md) | 추가한 지식·스킬·환경·감사 기능의 전체 레포 연결과 문서 구조·중복·현재 설명 검토 |
| [harness-connection-audit](harness-connection-audit/index.md) | 하네스 지침·스킬·CLI·훅·설정·검증·기록 사이의 끊긴 연결을 현재 근거와 실제 경로로 전반 조사한다 |
| [harness-connection-repairs](harness-connection-repairs/index.md) | 전체 검사를 막는 조사 JSON 등록 누락과 완료 근거의 worktree 의존 경로를 고친다 |
| [hook-diagnostics](hook-diagnostics/index.md) | 추가 모델 호출·검사 횟수 증가 없이 훅 실패의 단계·원인 코드·시간과 정적 검사 findings/stale를 안전하게 구분한다 |
| [hook-recovery](hook-recovery/index.md) | 훅 실패 기록을 현재 에이전트에 전달하고 미해결 조회·검증 근거에 따른 해결·재개 시 재노출까지 연결한다 |
| [lifecycle-hooks](lifecycle-hooks/index.md) | 세션 범위 Stop 알림·Interrupt 재개·선택적 정적 검사·명백한 원격 쓰기 감지 훅 연결 |
| [mcp-web-hooks](mcp-web-hooks/index.md) | 연결된 MCP 호출에 훅 안내·오류 판별·변경 후 정적 점검을 적용하고 내장 웹검색에는 명시적인 전후 검증 절차를 연결한다 |
| [python-expat-repair](python-expat-repair/index.md) | 기본 Python의 Expat 연결 오류를 복구해 XML 및 하네스 검사가 임시 환경변수 없이 동작하게 한다 |
| [reasons-design-gates](reasons-design-gates/index.md) | REASONS 설계·정렬 근거와 docs의 변경 분류를 연결하고 모든 구현 라우트 진입에서 최신 설계/검토/범위/미결정을 확인한다 |
| [security-convergence-review](security-convergence-review/index.md) | 보안 검사기의 거짓 통과·경합·누락을 재현하고 검토한 소스 버전과 남은 환경 한계를 보고한다. |
| [skill-route-graph](skill-route-graph/index.md) | 스킬별 라우트 계약과 call/return·transition·재진입 그래프를 구현하고 조건/검증/대기/반복을 제어한다 |
| [skills-consolidation](skills-consolidation/index.md) | 스킬 14개를 유지하면서 학습·브라우저 상세 절차를 담당 스킬로 모으고 문서 작업의 불필요한 읽기를 줄인다 |
| [spdd-reasons-research](spdd-reasons-research/index.md) | 조사한 SPDD/REASONS 원문과 도구를 현재 docs·계획·그래프·증거 하네스에 대조하여 의도/경계 선합의와 양방향 문서화의 보완 설계를 제안한다 |
| [top-down-planning](top-down-planning/index.md) | 사람이 정한 목표·마일스톤에서 요구·성공 조건·갭·작업을 연결하고 작업 전후 현재 근거로 계획을 갱신하는 하네스 절차 보강 |
| [verification-defaults](verification-defaults/index.md) | 검증해줘 같은 짧은 요청을 대상에 맞는 실행·정상/실패·회귀·구조·보안·관련 E2E의 기본 검증 계약으로 연결한다 |

지도에서 필요한 작업만 고른 뒤 해당 index의 역할 설명으로 원문을 선택한다. 현재 상태·완료 근거는 task/evidence가 정본이며 전체 notes·로그를 한 번에 읽지 않는다.

- [project-document-layout](project-document-layout/index.md): 프로젝트 문서를 docs/<프로젝트>/와 기능별 폴더로 관리하고 문서·인덱스·선택 조건을 함께 갱신한다

- [harness-connection-recheck](harness-connection-recheck/index.md): 현재 하네스 연결을 재점검하고 동시 문서 지도·worktree 검증 입력 경계의 재현 결함을 보완한다

- [document-delivery-defaults](document-delivery-defaults/index.md): 요구 문서의 8단계 안내와 기능 단위 구현·검증·다음 작업 판단을 기본 절차로 연결

- [verification-record-reuse](verification-record-reuse/index.md): 인덱스 중심 읽기를 명확히 하고 무관한 작업 기록이 검사 캐시·완료 근거·flow를 무효화하지 않게 한다

- [research-data-analysis](research-data-analysis/index.md): 공식·원저 자료로 CSV/JSON 데이터 분석 방법론을 조사하고 research의 질문·품질·해석·재현 절차를 보완한다

- [intent-contract](intent-contract/index.md): 발견 기록과 설계 의도 계약을 분리해 범위 내 결함 추가가 설계 정렬·flow 재시작을 강제하지 않게 한다

- [harness-work-efficiency](harness-work-efficiency/index.md): 반복 읽기·조사·검증·기록의 낭비를 줄이되 실제 근거와 의미 판단을 보존한다

- [project-explanation](project-explanation/index.md): 프로젝트 설명을 작업 중 누적하고 최종 상태에서 근거 기반 문답을 작성하는 절차 연결

- [conditional-doc-flow](conditional-doc-flow/index.md): 문서 내용 해시가 바뀌지 않은 구현 flow는 검증 후 문서 단계를 생략하고 변경 문서는 기존 절차로 이어간다

- [removed-project-links](removed-project-links/index.md): 삭제된 docs/projects 폴더를 가리키는 현재 문서 지도 링크를 제거한다

- [hook-notice-dedup](hook-notice-dedup/index.md): 같은 정적 오류의 반복 알림과 확인된 타 세션 담당 진단의 간섭을 줄인다
