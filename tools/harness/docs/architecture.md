# 공통 하네스 구조

2026-10-30. 사용자 합의: 범용 프로젝트 기반, Svelte 프론트·Python 백엔드,
레포 단위 재현, 요구사항 기준 검증과 비용 관리. 2026-10-31 PostgreSQL 사용을 추가 확정했다. 특정 서비스·DB 버전/ORM/확장·작업용 모델은 정하지 않았다.

```text
AGENTS.md                         공통 작업 규칙과 시작 안내
.agents/
  context.toml                    작업별 읽기 조건
  skills/<스킬>/
    SKILL.md                      적용 조건과 작업 절차
    references/                   상세 규칙·예제·실패 조건
    assets/                       해당 스킬의 양식·설정 예제
.codex/config.toml                Codex MCP·훅 기능 설정
.codex/hooks.json                 학습·메타데이터 생명주기 훅
tools/harness/                   하네스 구현을 모은 위치
  run.py                         모든 Python 명령의 진입점
  harness.toml                   스택·검사 명령·적용 경로
  harness/                       점검·맥락 선택·검사·기록 생성
    routing/                     모델 목록·분류·추천·실행·프롬프트 인수인계
  policies/                      잠정 모델 추천 정책
  scripts/                       학습 훅·브라우저 MCP·Playwright 연결
  browser/                       선택적 브라우저 MCP 의존성
  security/                      선택적 AgentShield 설치 명세(실엔진 미설치)
  tests/                         하네스 자체 회귀 검사
  docs/                          사용법·설계·도입 근거
docs/
  projects/<이름>/               서비스 요구·규칙·workflow.toml
  tasks/<이름>/                  작업 목표·근거·인수인계
  knowledge/catalog.json         검토 지식·조건·증거·대체의 정본
.runtime/                        검사 결과·로그·재사용 캐시
.cache/                          설치 캐시
.venv/                           각 노트북에서 만드는 Python 환경
```

2026-10-31 구조 정리: 하네스 구현과 서비스 자료를 구분하고 공통 실행 진입점을 만들었다.
`docs/tasks/`는 task 명령을 처음 실행할 때 생성한다. 서비스 코드 위치와 프레임워크는 아직 정하지 않았다.
스킬·참조·양식은 복제하지 않고 관련 스킬 옆에서 관리한다.
루트 README는 사용 시작 안내, 이 문서는 하네스 내부 설명, 루트 docs는 서비스 자료를 담당한다.

명령은 레포 루트에서 `python3 tools/harness/run.py <명령>`으로 실행한다.
모델 추천은 선택적 catalog/route를 사용한다. 일반 작업은 현재 대화창에서 수행하고, 별도 실행 방식을 직접 선택할 때만 run/chat을 사용한다.
자동 대화창 라우팅·인수인계 훅은 미등록 상태다. [선택적 실행과 검증 한계](execution.md)를 따른다.
내부 Python 패키지는 실행기가 경로를 설정하므로 별도 pip 설치나 전역 PYTHONPATH가 필요 없다.


요청 → 맥락·완료 기준 → 필요한 연구/실험/설계 → 작은 구현 → 범위별 검사 → 근거 대조 → 다음 작업으로 이어간다.
모든 요청에 모든 단계·스킬·문서를 강제하지 않는다. 자동 에이전트 팀이나 고정 재시도 예산을 추가하지 않았다.

## 내부 코드를 수정할 때

아래 경로는 이 문서가 있는 tools/harness/docs 기준이다. 루트 AGENTS.md의 구조 지도에서 하네스 구현 작업으로 연결된다.

| 코드 | 담당 기능 |
| --- | --- |
| [run.py](../run.py), [harness/cli.py](../harness/cli.py) | 공통 진입점·하위 명령·출력 |
| [harness/core.py](../harness/core.py), [harness/doctor.py](../harness/doctor.py) | 경로·설정·소스 상태와 정적 점검 |
| [harness/context.py](../harness/context.py) | 작업 종류·주제·경로에 맞는 읽기 자료 선택 |
| [harness/knowledge.py](../harness/knowledge.py), [harness/knowledge_hooks.py](../harness/knowledge_hooks.py) | [학습·공유 계약](knowledge.md). catalog를 CLI에서 검토하고 context/SessionStart가 현재 증거를 가진 항목을 읽는다. .codex/hooks.json → [scripts/knowledge-hook.py](../scripts/knowledge-hook.py)가 안내·메타데이터 기록으로 연결된다. |
| [harness/skills.py](../harness/skills.py) | [스킬 작성 계약](skill-authoring.md). maintain-skills → skill create/from-knowledge → SKILL.md와 context 등록. 적용 판단·본문 작성·품질 검토는 에이전트가 맡는다. |
| [harness/environment.py](../harness/environment.py) | [환경 계약](environment.md). setup-environment → environment inspect/install → 선언/lock 확인·명시적인 고정 설치. setup은 읽기 전용 inspect만 호출한다. |
| [harness/agent_config.py](../harness/agent_config.py) | [설정 감사 계약](security.md#codex-설정과-선택적-agentshield). security-review → security config. 기본 agent-config 등록 검사와 별도 AgentShield 옵션을 구분한다. |
| [harness/workflows.py](../harness/workflows.py), [harness/tasks.py](../harness/tasks.py) | 프로젝트 프로필·작업 기록의 생성과 검증 |
| [harness/checks.py](../harness/checks.py) | 검사 선택·실행·근거·재사용·Git index 사본 검증 |
| [harness/check_snapshots.py](../harness/check_snapshots.py) | 동시 편집 중 현재 소스의 고정 사본 검사와 출처 기록 |
| [harness/processes.py](../harness/processes.py) | 일반 check/실험의 시간·출력 제한, 프로세스 그룹 정리와 실패 보고 |
| [harness/provenance.py](../harness/provenance.py), [harness/evidence.py](../harness/evidence.py) | 파일·환경 지문, typed 증거, 기준별 리뷰와 완료 기록 |
| [harness/completion_review.py](../harness/completion_review.py) | 작업별 검토 영역·발견/처리 라운드·실제 회귀 증거의 완료 조건 |
| [harness/experiments.py](../harness/experiments.py) | 선언한 프로토콜의 로컬 반복·실패·지표·집계·비교 |
| [harness/evaluation.py](../harness/evaluation.py), [harness/pilot.py](../harness/pilot.py) | 저장된 작업 평가, 알려진 답을 쓰는 여섯 유형의 워크플로 재현 |
| [harness/workspaces.py](../harness/workspaces.py) | 작업 worktree·통합 검토 공간·겹친 경로·충돌·합친 결과 검사 |
| [harness/mcp.py](../harness/mcp.py) | HTTP MCP 연결 점검 |
| [harness/security.py](../harness/security.py) | 제한된 비밀값 패턴 검사·격리된 의존성 조회·응답 검증 |
| [harness/security_profiles.py](../harness/security_profiles.py) | 프로젝트 보안 문서 해시·필수 테스트 연결과 범위별 미결 판정 |
| [routing/catalog.py](../harness/routing/catalog.py) | 모델 목록 조회·정규화 |
| [routing/classify.py](../harness/routing/classify.py) | 규칙 분류·선택적인 Codex 분류 호출 |
| [routing/policy.py](../harness/routing/policy.py) | 정책 검사·모델/추론 조합 선택 |
| [routing/cli.py](../harness/routing/cli.py) | 모델 추천 명령의 입력·출력 |
| [test_routing.py](../tests/test_routing.py) | 실제 모델 생성 호출 없이 추천기 동작 검사 |
| [routing/execution.py](../harness/routing/execution.py) | 명시적으로 선택한 run/chat의 라우팅·입력 스냅샷·실행 기록·대화 맥락 |
| [routing/worker.py](../harness/routing/worker.py) | 선택 모델의 프로세스 실행·시간/출력 한도·설정 관측 |
| [routing/hooks.py](../harness/routing/hooks.py), [route_prompt.py](../route_prompt.py) | 미등록 보관 코드: UserPromptSubmit 추천·인수인계 |
| [test_routed_execution.py](../tests/test_routed_execution.py) | 대체 CLI의 분류→작업 실행·오류·대화·훅 인수인계 통합 검사 |
| [tests/](../tests/) | 점검·검사·프로필·맥락 선택·E2E 연결·경로 이동 회귀 검사 |

## 책임과 현재 경계

- AGENTS.md는 기준을 지시한다. 실행기는 명령의 종료 결과와 검사 범위를 기록한다.
- `check`의 통과는 선택한 등록 검사에 한정된다. 제품 요구 전체의 자동 수용을 뜻하지 않는다.
- `route`의 ready는 후보 선택이다. 자동 작업 실행·모델 전환·품질 보장을 뜻하지 않는다.
- 프로젝트 주제는 docs/projects 자료에 저장하고 스택·의존성·API·디자인 선택을 기록한다.
- 실제 앱 코드의 위치는 시작 시 정한다. frontend/backend 디렉터리와 별도 서비스 저장소를 미리 만들지 않는다.
- PostgreSQL 사용은 확정했다. SvelteKit·FastAPI·ORM·DB 버전/확장·클라이언트 생성 도구·색상·서체는 아직 후보 또는 미정이다.
- 디자인은 [템플릿](../../../.agents/skills/design-first/assets/design-system.md)과 스킬의 절차만 준비했다. 실제 값은 사용자와 정한다.
- API에서는 Python 정의 → OpenAPI → TS 타입·타입을 이용한 호출의 연결을 우선 검토한다.
  생성물 갱신·오류 계약·버전 고정도 함께 설정하고 타입 검사와 런타임 검증을 구분한다.

## 단계별 실제 구현

| 영역 | 현재 가능 | 아직 없는 것 |
| --- | --- | --- |
| 모델 선택과 실행 | 선택적 catalog/route와 명시적으로 실행한 run/chat, 정책 검사 | 일반 대화창 자동 라우팅은 보류·실모델 실행 미검증·서버 내부 모델/최적성 보증 없음 |
| 워크플로 | 조건별 원문 읽기·프로필·작업 기록·종류별 증거·리뷰 연결 완료·인수인계 | 자동 멀티에이전트 오케스트레이터·연구 진실 판단기 |
| 실험/평가 | 로컬 프로토콜 실행·조건 일치 비교·실패 집계·저장된 작업/여섯 유형 파일럿 평가 | 대규모 분산 실험·자동 모델 비교·독립 품질 개선의 보증 |
| 검증 | 공유 영향 선택·스모크/전체 구분·unittest/JUnit·로그·재사용·index 사본 | 임의 앱의 완전한 영향 분석·제품 전체 자동 승인 |
| E2E | 독립 스킬·시나리오/서버 설정 템플릿·로컬 runner 연결 | 프로젝트별 실제 앱·데이터·수용 시나리오 |
| 보안 | 통합 스킬·프로젝트 보안 양식·오프라인 패턴 검사·별도 advisory 조회 | 모든 취약점 탐지·임의 앱 자동 침투 검사·OS 실행 격리 보증 |
| 재현 | 표준 Python 도구·Codex 설정·레포 스킬 직접 사용 | 모든 OS·새 노트북에서 실측한 설치 보증 |
| 외부 도구 | 공식 HTTP MCP 구성·연결 점검, 선택적 브라우저 설치 | 현재 세션에 새 도구가 자동 추가된다는 보장 |
| 학습·공유 | 후보/검토/채택/대체·범위별 현재 증거·검색·bundle 공유·스킬 생성 | 원문 자동 학습·진위 자동 판정·개인 전역 규칙 자동 승격 |
| 환경 준비 | manifest/lock 기반 선택·충돌 거부·고정 설치·스크립트 기본 비활성 | 모든 workspace/plugin/OS 지원·관리자 자체 자동 설치 |

실행: [검증](verification.md), [작업](workflows.md), [도구와 설치](tools.md).
기존 모델 라우터의 상세 설계는 [design.md](design.md)를 유지한다.
초기 라우터의 출처·당시 결정은 [2026-10-22 참고 기록](references.md)에 있다. 현재 사용 계약은 usage/execution이며 초기 기록을 현재 가용성 근거로 쓰지 않는다.
