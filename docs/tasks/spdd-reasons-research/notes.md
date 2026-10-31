# SPDD/REASONS 기반 docs·하네스 보완 조사

2026-10-31. 현재 요청은 Thoughtworks 저자의 SPDD와 REASONS를 꼼꼼히 조사해 코드 전에 의도/경계를 맞추는 보완 설계를 판단하는 것이다. 일반 edge reason과 REASONS Canvas를 구분한다.

## 조사/검증 계획

양쪽 전체 과거 기록에서 주제·프로젝트·기존 결정을 검색하고 관련 Codex 원문과 Claude 관련 기록을 확인했다. Claude의 관련 SPDD 원문은 검색에서 발견하지 못했고 기존 읽은 무변경 맥락을 재사용했다. 접근 가능한 저장소와 현재 작성한 그래프/계획·docs를 대조한다.
Thoughtworks 저자의 Martin Fowler 원문, 연결된 open-spdd와 실제 핵심 템플릿을 읽는다. GitHub metadata/commit 조회에서3991ffa2cd6670fdb6f329ca62799ccb96d0e7d9를 확인했다. 이후 GitHub tree API는 로컬/웹 접근이 실패해 raw/HTML 원문으로 필요한 범위를 확인한다. 실행/설치/생성 도구를 돌리지 않고 템플릿을 자료로 읽는다.
문서/조사 산출물과 인덱스만 작성하며 실제 docs 스킬·flow 실행기 보완은 구현 전 제안으로 구분한다. 현재 코드의 설계 입력 게이트를 로컬 격리 사례로 확인한다. 제품 UI 변경이나 앱 E2E, 전체 하네스 회귀 재실행을 하지 않는다. 기존37x 테스트 이력을 이번 조사 완료로 재사용하지 않는다. doctor·원문/링크/명령·기준별 연구 리뷰를 확인한다.

## 최종 결론/산출물

하네스의 이동/근거 제어와 코드 전 설계 계약을 구분했다. 기존14개 스킬을 유지하고 plan-project의 분석·REASONS 설계/정렬, docs-maintenance의 정본·변경 분류·인덱스, flow의 모든 구현 진입에서 최신 설계/정렬 근거 확인을 단계별 제안했다. REASONS7관점과 기존reason은 다르다. 요구 변경·구현 결함·동작 보존 리팩터링·문서 오기의 돌아갈 위치를 구분했다.
현재 Python/Svelte/PostgreSQL은 설계 없이request만으로 시작할 수 있었고 단순label artifact로 계획의 기계적 passed가 가능했다. 실제 코드4관측은 .runtime/spdd-research/current-gate-observations.json에 보존했다. 이는 새 SPDD 요구의 준비 검사 공백이며 기존 제어기 계약 위반을 발견한 것으로 보고하지 않았다.
보고서는 tools/harness/docs/spdd-reasons-research.md, 당시 검토 사본은 REPORT에 묶었다. 하네스 문서 지도·작업 지도에 조사/제안 상태로 연결했다. 원문10개를 출처별 관측/한계/버전 기록으로 묶고 읽은 범위를 분리했다. 기존스킬/실행기/회귀 해시가 보존됐으며 새 설치/전역 설정/remote 쓰기/커밋·푸시 없음.

## 검증과 범위

현재 원문/링크·코드/지원 범위 대조와 doctor가 통과했다. 새 제품/실행기 코드를 바꾸지 않아 전체 회귀·앱 E2E는 재실행하지 않았다. 이전373개 검사 통과를 이번 SPDD 기능의 검증으로 차용하지 않았다. 새로운 준비 게이트·제안 라우트·실제 기능의12수용 사례는 후속 구현 기준이다.
research:evidence 흐름에서 원문·실제 관측·보고서/문서 검증 근거를 연결하고 finished를 확인했다. 자체 기준별 연구 리뷰이며 독립 평가가 아니다. REPORT/PROBE/PRESERVED/DOCS와 원문별source를 task에 연결해 완료한다.
