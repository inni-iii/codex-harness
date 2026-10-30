# 하네스 실행 도구

하네스 구현·설정·정책·브라우저 연결·자체 테스트·설명서를 이 폴더에서 관리한다.
공통 작업 지침은 [루트 AGENTS.md](../../AGENTS.md)와 [.agents](../../.agents/README.md),
서비스별 자료는 [루트 docs](../../docs/README.md)에 있다.

모든 명령은 레포 루트 기준이다. 활성 Python 3.11 이상과 정상적인 표준 XML 모듈이 필요하다.

```sh
python3 tools/harness/run.py --help
python3 tools/harness/run.py setup
python3 tools/harness/run.py doctor
python3 tools/harness/run.py context --kind plan --read
python3 tools/harness/run.py check --full
python3 tools/harness/run.py route --help
python3 tools/harness/run.py run --help
python3 tools/harness/run.py chat --help
```

| 위치 | 역할 |
| --- | --- |
| `run.py` | 공통 CLI 진입점 |
| `harness/` | 점검·자료 선택·검사 실행·프로젝트/작업 생성 |
| `harness/routing/` | 모델 목록·분류·추천·선택 모델 실행·훅 인수인계 |
| `route_prompt.py` | 미등록 상태로 보관한 UserPromptSubmit 훅 코드 |
| `harness.toml` | 검사 명령·적용 경로·기본 프로젝트 프로필 선택 |
| `policies/` | 잠정 모델 추천 기준 |
| `scripts/` | 학습 훅·브라우저 MCP·프로젝트 로컬 Playwright runner 연결 |
| `browser/` | 선택적 Playwright MCP 패키지와 잠금 파일 |
| `security/` | 선택적 AgentShield 설치 명세. 배포본/잠금·실엔진 검증은 미확인 |
| `tests/` | 하네스 자체 동작과 경로 이동의 회귀 검사 |
| `docs/` | 사용법·계약·설계·스킬 선별·검증 근거 |

검사·프로필·context에 쓰는 경로는 설정 파일의 위치와 관계없이 레포 루트 기준이다.
새 서비스의 검사 명령은 docs/projects의 workflow.toml에 등록한다.
하네스 테스트가 새 서비스 검사를 대신하지 않는다. route는 선택적 추천 도구이며 run/chat도 명시적으로 선택할 때만 사용한다.
로그·캐시는 루트 .runtime/.cache, 가상환경은 루트 .venv에 유지한다. 설치 결과는 공유하지 않는다.

상세 안내: [구조](docs/architecture.md), [검증](docs/verification.md),
[로컬 보안](docs/security.md), [스킬 관리](docs/skill-authoring.md),
[학습·공유](docs/knowledge.md), [프로젝트 의존성](docs/environment.md),
[프로젝트 워크플로](docs/project-workflows.md), [설치와 외부 도구](docs/tools.md), [모델 추천](docs/usage.md).
선택 도구의 실행 계약·자동 연결 보류·관측 한계는 [모델 실행](docs/execution.md)을 따른다.

2026-10-31에 루트에 흩어져 있던 하네스 코드·설정·정책·테스트·설명서를 이곳으로 모았다.
이전 Python 모듈명과 scripts/harness.py 대신 run.py 하위 명령을 사용한다.
스킬 전용 양식은 각 스킬의 assets에, 서비스 자료와 작업 기록은 루트 docs에 모았다.
