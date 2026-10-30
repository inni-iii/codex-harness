# Codex Harness

프로젝트 주제가 정해지기 전에 준비하는 범용 하네스 기반 레포.
Svelte 프론트·Python 백엔드·PostgreSQL 프로젝트에 공통 지침·도구·절차를 재사용한다.
개인 전역 설정을 복사하지 않고 다른 노트북에서도 구성할 수 있도록 준비한다.

## 어디를 수정할지

| 목적 | 위치 |
| --- | --- |
| 공통 작업 규칙·시작 명령 | [AGENTS.md](AGENTS.md) |
| 작업별 지침·상세 규칙·전용 양식 | [.agents/skills/](.agents/skills/), [읽기 안내](.agents/README.md) |
| Codex·MCP 설정 | [.codex/config.toml](.codex/config.toml) |
| 하네스 실행 기능·설정·자체 테스트 | [tools/harness/](tools/harness/README.md) |
| 실제 서비스의 요구·설계·결정·작업 기록 | [docs/](docs/README.md) |
| 문서를 찾고 필요한 원문만 읽기 | [문서 인덱스](docs/index.md) → 프로젝트/하네스별 지도 |

서비스 코드는 주제가 정해질 때 위치를 정한다. 하네스 Python 코드와 서비스 백엔드는 별개다.
Codex는 AGENTS.md로 시작하고 관련 스킬을 선택해 필요한 참조를 읽는다.
.agents 안의 모든 파일이 자동으로 주입되는 것은 아니다. context 명령은 읽기 대상을 안내하는 로컬 보조 도구다.

## 시작

Git과 Python 3.11 이상을 준비하고 레포 루트에서 실행한다.
Python 환경을 분리하려면 먼저 아래처럼 레포 안에 가상환경을 만든다. .venv는 Git에 넣지 않고 각 노트북에서 다시 만든다.

```sh
python3 -m venv .venv
source .venv/bin/activate
python3 -c "import tomllib, pyexpat"
```

표준 XML 모듈 import가 실패하면 해당 Python 설치를 확인하거나 정상 동작하는 Python으로 가상환경을 만든다.
하네스가 개인 전역 설정을 수정하지는 않는다. 아래 명령은 활성 환경의 Python을 사용한다.

```sh
python3 tools/harness/run.py setup
python3 tools/harness/run.py doctor
python3 tools/harness/run.py check --full
```

현재 Python 도구는 표준 라이브러리만 사용한다. Make가 있으면 make setup/doctor/check/test도 사용할 수 있다.
Codex는 별도로 설치·로그인한 뒤 레포 루트에서 시작한다.
[설치와 도구 안내](tools/harness/docs/tools.md)에 MCP 신뢰·연결 점검과 선택적 브라우저 설치를 설명한다.

기본 작업은 현재 대화창 모델로 진행한다. 모델·추론 강도 추천이 필요할 때 `catalog`/`route`를 직접 사용한다.
라우터 호출은 의무가 아니며 일반 대화창의 자동 추천·인수인계 훅은 미등록 상태다.
별도 모델 실행을 명시적으로 선택하면 `run`/`chat`을 사용할 수 있다. [선택적 실행과 한계](tools/harness/docs/execution.md)를 확인한다.

## 현재 동작

- Codex 공통 AGENTS.md와 작업별 스킬. [E2E 스킬](.agents/skills/e2e-testing/SKILL.md)은 관련 UI 흐름의 Playwright 작성·실행·실패 분석과 설정 템플릿을 제공한다.
- [문서 관리 스킬](.agents/skills/docs-maintenance/SKILL.md): 분류·이동·최신화와 출처 기반 LLM 위키의 반영·질문·점검. [도입 조사와 선택 근거](tools/harness/docs/docs-maintenance-research.md)를 참고한다.
- [학습·기억 관리](.agents/skills/maintain-knowledge/SKILL.md): 프로젝트/공통 범위, 근거를 연결한 채택과 대체, 검색·공유. [사용법과 훅 신뢰 조건](tools/harness/docs/knowledge.md)을 확인한다.
- [스킬 작성·개선](.agents/skills/maintain-skills/SKILL.md): 레포 스킬 생성·등록과 검토한 공통 지식의 전환. 개인 전역 스킬 설치 없이 사용한다.
- [환경 준비](.agents/skills/setup-environment/SKILL.md): 저장소 선언·lockfile 기반 관리자 선택과 frozen 설치. [지원 범위](tools/harness/docs/environment.md)를 확인한다.
- [Postgres 스킬](.agents/skills/postgres/SKILL.md)의 스키마·migration·쿼리 성능·실제 DB 검증, [연구 검색 지침](.agents/skills/research/references/retrieval.md)의 질문 분해·출처 보존·검색/답변 실패 구분.
- 스킬의 절차·예제·실패 조건을 담은 참조 문서와 context 명령의 조건별 원문 읽기.
- OpenAI·Svelte 공식 HTTP MCP 설정과 명시적인 연결 확인 명령.
- .agents/skills에 있는 스킬을 Codex가 직접 사용하며 별도 복사본을 만들지 않는다.
- 변경 범위별 검사 선택, 원본 로그·종료 코드·테스트 수 기록, 조건부 결과 재사용.
- Git index의 정확한 사본에서 staged 소스와 검사기를 실행하는 검증.
- edit/feature/integration/final 경계별 검사 선택과 미룬 검사 표시. 의미 있는 사용자 기능 묶음 완성 시 E2E를 수행하고 시작 전에 범위를 알린다.
- [세션·통합 도구](tools/harness/docs/sessions.md): 작업용 worktree 생성, 별도 통합 검토 공간·중복 경로·텍스트 충돌 기록, 합친 상태의 검사. 의미상 충돌의 최종 판단은 에이전트가 수행한다.
- 프로젝트·디자인·실험·결정 템플릿과 작업 기록 생성.
- [완료 계약](tools/harness/docs/completion.md): 종류별 실제 증거·파일 해시·검사 대상 상태·기준별 리뷰를 연결한 작업 완료.
- [한 요청 안의 검토·보완과 회귀 보존](tools/harness/docs/review-rounds.md): 발견 사항을 같은 요청에서 처리하고 최종 재검토·결함별 실제 회귀 근거를 완료에 연결.
- [로컬 실험](tools/harness/docs/experiments.md): 선언한 입력·후보·지표·seed·예산으로 실행하고 원본·실패·집계를 보존한 비교.
- [평가 파일럿](tools/harness/docs/harness-evaluation.md): 여섯 작업 유형의 실제 도구 연결을 재현하고, 독립적인 에이전트 성능 평가와 구분.
- 프로젝트 프로필 생성·선택, 공유 변경의 검사 확대, 가벼운 공통 스모크와 전체 검사 구분.
- 보안 경계·요구/결함 리뷰·인수인계·학습 기록·품질 기준·로그·외부 호출을 조건에 맞게 읽는 상세 절차.
- [통합 보안 스킬](.agents/skills/security-review/SKILL.md), 프로젝트별 보안 설계 양식·부정 테스트 절차, 오프라인 비밀값 후보 검사와 별도 의존성 조회. [실행 범위와 한계](tools/harness/docs/security.md)를 확인한다.
- unittest/JUnit 결과의 실행 수·skip·실패 확인. JUnit은 Python XML 모듈이 동작해야 한다.
- 선택적 catalog/route 모델·추론 추천기와 명시적으로 사용하는 run/chat 실행 도구. 일반 대화창의 자동 라우팅·인수인계는 보류했다.

등록 검사 통과와 제품 요구 충족은 별개다. 새로운 앱 파일에 대응 검사가 없으면 설정 필요로 보고한다.
run/chat을 직접 선택하면 해당 명령 안에서 라우팅 후 별도 모델을 실행한다. 일반 작업에 이 명령을 강제하지 않으며 에이전트 팀·제품 전체 완료 판정은 없다.
PostgreSQL 사용은 확정했다. 프로젝트 주제·SvelteKit/FastAPI·ORM·DB 버전/확장·디자인 값·작업용 모델은 미리 고정하지 않았다.
외부 MCP 연결·브라우저 설치·다른 OS 지원은 실제 점검 결과와 구분한다.

## 자주 쓰는 명령

```sh
python3 tools/harness/run.py check --plan
python3 tools/harness/run.py check --checkpoint edit
python3 tools/harness/run.py check --checkpoint feature
python3 tools/harness/run.py session status
python3 tools/harness/run.py context --kind research --topic technical-choice --read
python3 tools/harness/run.py context --kind review --paths tools/harness/harness/context.py --read
python3 tools/harness/run.py context --kind plan --topic resume --read
python3 tools/harness/run.py check --paths AGENTS.md
python3 tools/harness/run.py check --reuse
python3 tools/harness/run.py check --staged
python3 tools/harness/run.py mcp-check
python3 tools/harness/run.py task first-research --kind research --goal "주제 조사" --acceptance "선택 근거와 한계를 정리한다"
```

check의 기본 범위는 현재 변경, --full은 등록 검사 전체다. --reuse는 적합한 동일 조건 결과에만 적용한다.
기본 checkpoint는 feature다. make check-quick은 edit, make check-feature는 feature이며, 프로젝트의 비싼 검사에 run_at을 등록해야 시점별로 구분된다.
세션 start·통합 prepare는 깨끗한 커밋 기준을 요구한다. 현재 첫 커밋이 없는 이 레포에서는 기준 마련 후 사용하며 자동으로 사용자 변경을 커밋하지 않는다.
--staged는 staging된 대상이 있어야 하며 스스로 git add하지 않는다.
MCP 연결 점검과 선택적 브라우저 설치는 네트워크를 사용한다. 기본 setup/doctor/check는 모델을 호출하지 않는다.

## 구조와 안내

- [공통 작업 지침](AGENTS.md)
- [전체 구조와 구현 경계](tools/harness/docs/architecture.md)
- [검증 명령·범위·결과 재사용](tools/harness/docs/verification.md)
- [작업별 최소 읽기·검사 시점·오케스트레이션 판단](tools/harness/docs/verification-audit.md)
- [로컬 보안 관리와 검사](tools/harness/docs/security.md), [전역 의존성 없는 스킬 관리](tools/harness/docs/skill-authoring.md)
- [연구·실험·구현·인수인계](tools/harness/docs/workflows.md)
- [프로젝트 워크플로 설정](tools/harness/docs/project-workflows.md)
- [스킬 선별·재작성 내역](tools/harness/docs/skill-sources.md), [하네스 평가 범위](tools/harness/docs/harness-evaluation.md)
- [설치·MCP·브라우저](tools/harness/docs/tools.md)
- [프로젝트 자료](docs/projects/README.md)
- [모델 라우터 사용법](tools/harness/docs/usage.md), [계약](tools/harness/docs/contracts.md), [기존 설계](tools/harness/docs/design.md)
- [선택적 모델 실행과 자동 연결 보류](tools/harness/docs/execution.md)
- [초기 설치 구성안과 미결정 사항](tools/harness/docs/repository-setup.md)

스킬은 .agents/skills에 한 번만 관리하고 Codex가 직접 읽는다.
실행 코드·설정·테스트·설명서는 tools/harness에 모은다.
프로젝트 자료는 docs/projects, 작업 조건·근거·인수인계는 docs/tasks에 저장한다.
코드 위치는 프로젝트 시작 시 정한다. 디자인은 템플릿을 이용해 사용자와 결정한 뒤 구현한다.

로그·캐시·인증 자료·의존성 설치 결과는 Git에서 제외한다.
공유 문서와 작업 기록에도 비밀값을 넣지 않는다.
