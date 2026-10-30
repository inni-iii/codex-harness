# 검증 하네스의 전체 연결·실행 범위 점검

2026-10-31. 범위: 지침·10개 레포 스킬·맥락 선택·프로젝트 프로필·검사 실행/재사용·
작업 증거/완료·실험/평가·E2E 연결·세션/통합/소스 사본 검증과 실제 자체 회귀 검사.
공개 저장소와 공식 문서를 비교했다. GitHub 연결·CI 도입·원격 쓰기·모델 팀 자동 실행은 하지 않는다.

판정: 로컬 범용 하네스의 기반과 실패 차단은 갖춰져 있다. 실제 서비스가 들어오면 프로젝트별 계약·검사·데이터·환경을 연결해야 한다.
현재 설정만으로 임의 서비스의 완전한 검증이나 에이전트의 지침 준수를 강제한다고 주장하지 않는다.

## 작업별로 최소한 읽고 필요한 검사를 선택하기

아래 명령은 레포 루트 기준이다. 공통 진입점은 `python3 tools/harness/run.py`이며 프로젝트에서 정한 정상 Python을 사용한다.
context는 읽기 대상을 고르는 명령이다. 목록을 받은 뒤 원문을 읽어야 하며 검사를 실행하지 않는다.
같은 세션에서 이미 읽은 변경 없는 원문은 재사용한다. 모든 문서를 매번 --read로 출력하지 않는다.

| 작업 | 맥락 선택 예 | 이번 작업의 검증 | 기본으로 강제하지 않을 것 |
| --- | --- | --- | --- |
| 작은 사실 조사 | context --kind research | 질문·원문·날짜/조건·반증·한계 대조 | 코드 전체 검사·브라우저·새 task |
| 큰 비교·복합 검색 | context --kind research --topic retrieval | 검색 누락·조건 차이·주장별 원문 연결 | RAG 설치·모델 팀·출처 개수만으로 품질 판정 |
| 실험 | context --kind experiment | 사전 프로토콜·실제 측정·전체 실패·동일 조건 비교 | 임의 반복·최고 결과 선택·유료 호출 |
| 시스템 설계 | context --kind design --topic quality | 관측 가능한 품질 시나리오·계약·위험·구현/검사 가능성 | 색상·서체·브라우저 실행 |
| UI 설계만 | context --kind design --topic ui-design | 디자인 계약·상태·후속 구현/검증 조건 | 구현용 전체 E2E 안내 자동 선택 |
| Python 구현 | context --kind implement --paths backend/items.py --topic backend | 관련 동작·오류·DB/API·회귀 | 무관한 프론트 전체 suite |
| PostgreSQL 변경 | context --kind implement --paths backend/migrations/001.sql --topic postgres | 실제 PostgreSQL의 제약·트랜잭션·migration·영향받는 쿼리 | SQLite로 PostgreSQL 특성 증명·운영 DB 변경 |
| Svelte 기능 구현 | context --kind implement --paths frontend/Form.svelte --topic ui | 타입/상태·API 연결·기능 완성 시 관련 사용자 흐름 | 편집/버튼마다 전체 E2E |
| 디버깅 | context --kind debug --paths 실제경로 | 수정 전 재현·좁은 수정·관련 회귀 | 모든 실패의 모델 상향·무조건 전체 재검사 |
| 기록 완료 | context --kind 현재종류 --paths docs/tasks/작업/task.json | 종류별 실제 증거·기준별 리뷰·현재 상태 대조 | 작은 답변마다 파일 작성·매번 사람 승인 |
| 작업 이어받기 | context --kind plan --topic resume | 기록된 결정·실패·남은 조건·다음 행동 복원 | 모든 과거 보고서를 현재 통과 결과로 재사용 |
| 다른 세션 작업 통합 | context --kind review --topic merge | 양쪽 의도·겹친 변경·합친 결과·의미상 충돌 | 텍스트 merge 성공을 요구 충족으로 판정 |

실제 경로와 주제만 지정한다. kinds/topics/paths는 OR이므로 Svelte 구현 경로를 넣고 UI 설계만 읽히리라 기대하지 않는다.
계획·코드 없는 UI 설계에는 ui-design, 화면 구현·상태·브라우저 검증에는 ui가 적합하다.

## 코드 검사의 시점과 확대 조건

| 경계 | 선택 기준 | 결과 해석 |
| --- | --- | --- |
| edit | 영향받는 빠른 검사, run_at에 따라 비싼 검사는 연기 | deferred 목록이 있으면 기능 전체 완료가 아님 |
| feature | 작성→저장→재조회처럼 사용자 결과 하나가 완성 | 해당 기능의 동작·연결·필요한 E2E |
| integration | 독립 변경을 합친 상태, 양쪽 변경과 공유 경계 | 기존 요구를 보존하는 통합 검토도 필요 |
| final | 제출 범위와 남은 위험을 판단 | final만 지정해도 전체 suite가 선택되는 것은 아님 |
| --full | 등록 검사 전체를 명시적으로 요청 | 등록하지 않은 제품 검사까지 생기는 것은 아님 |

공유 schema·인증·공통 컴포넌트·계약 변경은 impacts로 관련 소비자의 검사를 확대한다.
새 코드에 대응하는 검사 경로가 없으면 needs_configuration이다. doctor·비밀값 패턴 검사로 대신하지 않는다.
정적 검사·타입·lint만으로 사용자 동작이 증명됐다고 하지 않는다. 필요한 행동 검사와 수용 기준별 리뷰를 연결한다.
외부 DB/서비스/브라우저처럼 상태에 의존하는 검사는 cacheable=false를 기본으로 판단한다.
재사용은 조건과 원본 무결성이 같을 때만 하고, 새 변경·실패·불확실성이 있을 때 관련 범위만 다시 검사한다.

보안 설계가 진행 중이어도 해당 로컬 검사는 실행할 수 있다. 영향받는 미결 사항은 checks_passed_security_pending으로 남겨
검사 실행 성공과 보안/전체 완료를 구분한다. 범위가 다른 세션까지 전역 잠금으로 막지 않는다.

## 확인한 누락과 이번 수정

1. 완료 리뷰 생성 후 review.json이 미등록 코드로 분류됐다. task.json과 함께 좁은 기록 예외로 넣었다.
   helper.py·임의 JSON을 제외해 실제 코드를 숨기지 않는 회귀도 확인한다.
2. 검사 설정의 time_out/cacheble 같은 오타와 run_after/parallel 같은 미지원 필드가 조용히 무시될 수 있었다.
   지원 필드를 엄격히 검사해 실행 전에 거부한다. 사용자가 의도한 시간/순서 제약이 적용됐다는 잘못된 전제를 막는다.
3. UI 설계에 넓은 ui 주제를 권하면 실제 구현의 E2E/브라우저 안내도 선택됐다.
   기존 ui-design 선택을 우선 안내하고, 순수 설계와 구현에서 읽는 범위가 달라지는지 회귀로 확인한다.

기존 소스 변경 감지·캐시 무결성·0개/전체skip/불안정 결과·단계별 연기·보안 미결·현재/과거 증거 구분은 유지한다.
새 병렬 작업용 소스 사본과 PostgreSQL 스킬은 다른 세션의 추가 작업을 보존한 상태에서 검사한다.
과거 보고서의 테스트 수를 현재 결과로 복사하지 않는다. 이번 실제 실행 수·종료 상태·시각·소스 상태는 .runtime/audit-current/에 둔다.

## 오케스트레이션은 언제 필요한가

| 형태 | 적용 상황 | 현재 하네스와의 관계 |
| --- | --- | --- |
| 코드가 정한 순서의 검사 | 검사 선택→실행→보고서→증거 검토 | 현재 CLI·checkpoint·manifest로 제공. 검사들은 현재 순차 실행 |
| 독립 테스트의 병렬 실행 | 데이터/포트/자원 격리를 증명하고 실제 시간이 병목일 때 | 각 프로젝트 runner에서 opt-in. 무조건 워커 수를 늘리지 않음 |
| 여러 작업 세션 격리 | 별도 기능이 서로의 작성 중 상태를 망가뜨릴 때 | worktree·통합 검토, 필요 시 현재 소스의 고정 사본 검사 |
| 여러 AI의 분담·종합 | 독립적인 큰 조사 갈래·서로 다른 경계의 검토가 이득일 때 | 권한 범위에서 선택적으로 사용. 범용 작업의 기본 필수 단계가 아님 |
| 장기 상태 그래프 | 많은 실행 분기·중단/복구·실패 재개·비용 관리가 실제로 필요할 때 | run/chat은 요청별 실행을 제공한다. 장기 상태 그래프는 없으며 측정한 필요가 생길 때 도입 검토 |

기본 권고는 **현재 에이전트가 작업별 범위를 판단하고, 결정적 도구가 실행·근거를 확인하는 구조**다.
작업 종류마다 고정된 AI 팀을 생성하거나 검사 통과 때까지 무제한 재시도하지 않는다.
멀티에이전트를 사용한다면 역할·입력·산출물·쓰기 담당·전체 호출/시간 예산·중단 조건·통합 검토자를 먼저 정한다.
작은 문구 수정이나 단일 결함에 연구/설계/구현/리뷰 에이전트를 모두 붙이지 않는다.

현재 task.depends_on은 관계를 남기는 메타데이터다. 자동 스케줄링·의존 작업 실행을 뜻하지 않는다.
source snapshot은 검사 중 대상이 바뀌는 것을 다루는 도구이며 세션 쓰기 충돌이나 의미상 병합을 자동 해결하지 않는다.
첫 커밋이 없는 메인 레포에 격리 기준을 만들기 위해 임의 커밋하지 않는다. 격리/통합 회귀는 임시 Git 레포에서 검사한다.

## 공개 구현과 비교한 근거

- [SvelteKit CONTRIBUTING](https://github.com/sveltejs/kit/blob/main/CONTRIBUTING.md): format/lint/check/unit와 통합 테스트를 나누고, 개별 통합 테스트의 로컬 실행 경로를 안내한다. 검사 구분을 참고하며 모든 단계의 매번 전체 실행으로 해석하지 않는다.
- [FastAPI test.sh](https://github.com/fastapi/fastapi/blob/master/scripts/test.sh)·[lint.sh](https://github.com/fastapi/fastapi/blob/master/scripts/lint.sh): 정해진 스크립트로 검사하고 pytest-xdist 병렬 실행을 사용한다. 이는 다중 LLM 팀과 구분되는 테스트 실행 조정의 실제 예다.
- [FastAPI full-stack Playwright workflow](https://github.com/fastapi/full-stack-fastapi-template/blob/master/.github/workflows/playwright.yml): 변경 경로 필터, 작업 의존 순서, shard, flaky 실패와 trace를 연결한다. 구조를 비교했으며 이 레포에 GitHub CI·업로드를 도입하지 않는다.
- [Playwright best practices](https://playwright.dev/docs/best-practices): 사용자에게 보이는 결과·테스트 격리·병렬 실행을 다룬다. 병렬성은 격리·자원을 갖춘 범위에서 사용한다.
- [Building effective agents](https://www.anthropic.com/research/building-effective-agents): 예측 가능한 workflow와 동적 agent를 구분하고 필요한 만큼 복잡도를 늘리도록 권한다. 자동 LLM 단계 추가가 모든 문제의 기본 해법은 아니다.
- [프로덕션 다중 에이전트 연구 사례](https://www.anthropic.com/research/multi-agent-research-system): 독립적인 여러 조사 갈래의 이득과 조정·토큰 비용의 증가를 함께 설명한다. 특정 회사의 결과를 우리 하네스의 성공률로 옮기지 않는다.
- [LangGraph 공식 레포](https://github.com/langchain-ai/langgraph)·[workflow/agent 문서](https://docs.langchain.com/oss/python/langgraph/workflows-agents): 장기 상태·복구와 orchestrator/worker 구현의 공개 사례다. 사용 사례의 존재를 전체 업계의 보급률로 해석하지 않는다.

따라서 현업·공개 저장소에서 검사 실행 조정과 다중 에이전트의 실제 사례는 확인할 수 있지만,
“대부분의 팀이 모든 개발·검증에 다중 AI 오케스트레이터를 쓴다”는 결론을 뒷받침할 대표성 있는 보급률 자료는 이번 조사에서 확인하지 않았다.

## 현재 검증의 경계

실제 서비스·PostgreSQL 테스트 데이터·브라우저 사용자 흐름은 프로젝트 시작 시 연결해야 한다.
자체 회귀나 알려진 답의 evaluate-pilot을 운영 서비스 E2E·독립적인 에이전트 품질 개선으로 표현하지 않는다.
이번 실행 환경은 POSIX 그룹 신호를 차단하므로 자손 정리 실측의 건너뜀을 명시한다. 권한 거부 시 실패 처리 검사는 별도로 확인한다.
환경 지문은 모든 설치 패키지·외부 DB/서비스 상태를 포착하지 않는다. 이런 조건은 명시하고 동일 결과 재사용을 보수적으로 판단한다.
context/AGENTS는 에이전트의 읽기·판단 지침이며 OS 실행 제한·자동 주입 hook·제품 전체 수용 판단기가 아니다.
