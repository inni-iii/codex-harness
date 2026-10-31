# 스킬 선별·재작성 기록

2026-10-30 첫 보강에서는 원본 SKILL.md 15개와 관련 참조·규칙·템플릿 10개를 본문 끝까지 읽었다.
합계 25개 파일 8,048줄이다. 이 숫자는 읽은 범위이며 스킬 품질의 증명이 아니다.
노트북의 모든 레포나 모든 스킬을 검토했다는 의미가 아니다.

외부 원본은 참고 자료로만 읽었고 전역 설정이나 원본 레포는 수정하지 않았다.
원문 파일을 통째로 복제하지 않고 판단 기준·실패 조건을 재작성했다.
이 문서의 원본 레포/경로 이름은 출처 식별용이다. 실행 시 해당 레포나 개인 절대경로를 요구하지 않는다.
이전의 7개 짧은 스킬은 이번에 절차·조건별 참조·예제로 보완했다.

## 2026-10-31 학습·스킬·환경·설정 감사의 후속 구현

사용자가 학습/공유 → 스킬 관리 → 설치/패키지 관리자 → 설정 감사 순서의 보완을 승인했다.
기존 11개에 maintain-knowledge, maintain-skills, setup-environment를 추가해 이 단계는 14개다.
아래 과거 기록의 '미이식/미지원'은 당시 판단이다. 여기서 대체한 범위와 여전히 미확인인 범위를 구분한다.

| 영역 | 원본/현재 지원 대조 | 채택과 남긴 경계 |
|---|---|---|
| continuous-learning-v2·learn-eval | mitam 원본은 .claude 관찰/개인 홈·백그라운드 모델 가정. 관찰 활성화와 단순 CLI 조회도 구분 필요 | 프로젝트/common 범위, candidate/evaluated/adopted/superseded, 이유·조건·현재 증거, 검색·안전한 bundle 공유를 로컬 도구로 구현. 개인 전역 승격·원문 수집·자동 점수 채택 제외 |
| compact/observer | 공식 Codex의 SessionStart/PreCompact/Stop과 저장 위치·stdin/stdout 계약을 확인 | .codex/hooks.json과 레포 스크립트. SessionStart는 검토 지식 안내, PreCompact/Stop은 task 경로/해시/상태만 저장. 압축 후 복원은 source=compact SessionStart 사용. 신뢰 전 native 실행은 미확인 |
| skill-create | 원본의 커밋 경로 선별 정규식 ^[a-f0-9]는 frontend/backend/docs/api 같은 정상 경로도 탈락시킬 수 있음. 현재 레포에는 HEAD도 없음 | 실제 본문 파일 또는 채택된 공통 지식에서 native 스킬+context 등록. Git 이력 필수화·커밋 자동 생성·고정 모델·전역 설치 제외 |
| setup/package-manager | mitam의 SKILL이 가리킨 install.py/setup-package-manager.js는 확인 경로에 없고 lib/package-manager.js만 있음. 개인 선호를 저장소에 우선하는 선택은 이식 목적과 충돌 | 공식 관리자별 frozen 계약으로 새 구현. 선언/lock 충돌·버전 불일치·상위 workspace를 사전 확인. Node/npm/pnpm/Yarn/Bun, Python/uv와 Poetry 감지. Poetry 자동 설치는 프로젝트 workflow로 남김 |
| AgentShield | Codex 규칙이 있는 공식 원본을 확인. 로컬 좁은 scanner와 동등하거나 더 나쁘다는 비교 실험은 없음 | 기본 Codex 설정 검사+선택적 원본 CLI 어댑터. 원본 정적 엔진은 미설치이며 실제 탐지 검증은 남음. 런타임 훅/자동 fix/추가 모델 제외 |

### Codex용 대안의 확인 범위

- [OpenAI skills](https://github.com/openai/skills): 공식 작성/설치 스킬의 구조·점진적 읽기·검증 원칙을 참고했다. 실행 의존성을 개인 전역 파일로 만들지 않고 레포 관리 절차와 도구를 작성했다.
- [ECC .codex 원문](https://github.com/affaan-m/ECC/blob/main/.codex/AGENTS.md): .agents/skills와 네이티브 훅 신뢰 검토를 안내하는 Codex 구성이 있다. sync 스크립트의 여러 MCP 일괄 등록·고정 모델 추천은 현재 요구와 맞지 않아 도입하지 않았다.
- [everything-openai-codex](https://github.com/mturac/everything-openai-codex), [codex-agent-setup](https://github.com/ndhananj/codex-agent-setup): Codex용이라고 공개된 대안도 찾았다. README/공개 구조 확인에 그쳤으며 전 파일·실행 지원을 검증하지 않았다. 첫 프로젝트의 CLI v2.1.0+ 안내와 실제 관측 0.166.0도 다르므로 이름이나 README만으로 설치 근거로 삼지 않았다.
- [AgentShield](https://github.com/affaan-m/agentshield): MIT·저장소 package.json 1.6.0/Node>=20, discovery·Codex 규칙·CLI·JSON 계약을 읽었다. [API 문서](https://github.com/affaan-m/agentshield/blob/main/API.md)는 내부 scanner import를 안정 API로 약속하지 않으므로 CLI를 선택했다. npm 배포본/integrity는 현재 DNS 실패로 검증하지 못했다.

### 공식 계약과 검증 방법

[공식 skills 계약](https://developers.openai.com/plugins/build/skills)의 name/description·선택 후 본문 읽기를 따르고, 레포의 context는 별도 보조 선택기로 유지한다.
[공식 hooks 계약](https://learn.chatgpt.com/docs/hooks)의 JSON 이벤트·matcher·command handler·추가 맥락 형태와 신뢰 검토를 대조했다.
로컬 CLI는 0.166.0, hooks는 stable/enabled로 관측했다. 이것이 다른 클라이언트/OS의 활성화나 이 레포 훅의 실제 이벤트 실행을 보증하지 않는다.
관리자 명령은 [npm ci](https://docs.npmjs.com/cli/v11/commands/npm-ci/), [pnpm install](https://pnpm.io/cli/install), [Yarn install](https://yarnpkg.com/cli/install), [Bun install](https://bun.sh/docs/pm/cli/install), [uv sync](https://docs.astral.sh/uv/concepts/projects/sync/), [Poetry sync](https://python-poetry.org/docs/cli/#sync)를 대조했다.
공개 main/현재 문서의 확인이며 원본을 특정 커밋으로 vendoring하거나 외부 스킬 문구를 통째로 복제하지 않았다.

구현/사용법: [지식](knowledge.md), [스킬](skill-authoring.md), [환경](environment.md), [설정 감사와 실엔진 미확인](security.md#codex-설정과-선택적-agentshield).
검증은 CLI 연결·범위/충돌/현재 증거·훅 stdin·실제 오프라인 npm/uv·외부 CLI 프로토콜을 구분한다. 고정 응답 fixture는 실제 AgentShield의 정확도 근거가 아니다.

## 2026-10-31 문서 관리·LLM Wiki 추가

후속 스킬 정리에서는 14개 스킬을 유지하고 plan-project의 학습 참조·양식을 maintain-knowledge로 이동했다.
Playwright 작성·시각/접근성·실패 절차는 e2e-testing에 모으고 verify-work의 browser 참조는 범위·완료 판단과 연결만 담당한다.
공통 검증 흐름은 유지하며 상세 코드 검증은 실제 경로 또는 code-review/code-verification, 발견·완료는 regression/completion 등 해당 주제로 읽는다.
이 변경은 스킬 통합이나 검증 생략이 아니라 상세 절차의 소유 위치와 선택 조건 정리다. 과거 아래 단계의 경로·개수는 당시 기록이다.

사용자 요청으로 공개 스킬·공식 문서를 병렬 조사하고 [docs-maintenance](../../../.agents/skills/docs-maintenance/SKILL.md)를 추가했다.
이번 문서 스킬은 직전 10개 구성에 추가했다. 아래 10/9/8/7개 표기는 각 단계의 이력이며 현재 전체 수는 실제 스킬과 context 등록에서 확인한다.
문서 구조·구현/결정 최신화·위키의 ingest/query/lint·변경 검증을 조건별 참조로 나눴다.
원본 근거·사용자 결정·실패 이유 보존, 생성 입력 관리, 링크/앵커/목차, 문서/코드 양방향 대조를 포함한다.
읽기 전용 질문은 자동 저장하지 않으며, 프로젝트 사실을 범용 스킬로 옮기지 않는다.
실제 원문·채택/제외·라이선스 확인 범위·검증 한계는 [도입 조사](docs-maintenance-research.md)에 기록했다.
외부 스킬 문구/코드를 복제하지 않고 한국어로 재작성했다. 기존 research·plan-project·verify-work와 knowledge 도구의 책임을 유지한다.
전역 hub·세션 자동수집·새 벡터 DB·사이트·CI·외부 발행·일괄 재승인 절차는 도입하지 않았다.

## 2026-10-31 PostgreSQL 확정과 연구 검색 재검토

사용자가 PostgreSQL 사용을 확정하고 DB 지침 추가를 요청했다. 기존의 DB 미정 판단을 대체한다.
이 단계에서는 스킬이 10개였다. 아래 과거 단계의 7/8/9개와 당시 DB 미정 설명은 이력이다.

| 다시 확인한 원본 | 이번 반영 | 수정·제외와 실제 범위 |
|---|---|---|
| mitam-math postgres-patterns·postgres-pro·database-migrations·database-optimizer의 SKILL.md, optimizer의 query-optimization/index-strategies 참조 | 독립 postgres 스킬과 schema/migrations/performance/testing 참조 4개, Python 연결과 context 읽기 조건 | ORM·서버 버전·확장은 미정. 원격 변경·복제/HA 의무·전역 서버 튜닝·고정 ID/메모리 정책은 제외. DB 설치/접속/실제 migration은 수행하지 않음 |
| rag-architect SKILL.md, retrieval-optimization의 질문 확장/재작성·metadata/시간 필터·분해·문맥 압축 구간, rag-evaluation의 지표/검색 진단/평가 절차 구간, chunking-strategies의 전략 비교/문서 구조/metadata 구간 | research/retrieval: 하위 질문·용어 확장·원문/버전/위치·중복 제거·문맥·검색 실패와 답변 실패 분리. 실제 RAG 구축 시의 기준선·권한/삭제·평가도 조건부 안내 | 참조 전체·모든 코드/API를 실행 검증한 것은 아님. 벡터 DB·추가 모델·hybrid/reranking 강제·고정 비용/성능/품질 수치는 미채택. 자동 RAG 실행기는 구현하지 않음 |
| websocket-engineer의 이전 감사와 대체 전송 방식 검토 | 현 단계는 배치 제안: python-backend의 조건부 실시간 참조를 중심으로 프론트 수명·보안·검증 연결 | 사용자가 가정형으로 위치를 질문한 단계이므로 WebSocket 스킬/코드/Redis는 추가하지 않음 |

DB 원본에서 nullable 컬럼 추가를 무잠금으로 표현한 부분, NOW() 기반 부분 인덱스, 모든 환경의 복제/풀러 의무, 쿼리 구문별 고정 성능 판단은 복제하지 않았다.
[ALTER TABLE](https://www.postgresql.org/docs/current/sql-altertable.html), [인덱스와 immutable/동시 생성 제약](https://www.postgresql.org/docs/current/sql-createindex.html), [EXPLAIN](https://www.postgresql.org/docs/current/using-explain.html), [RLS](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)를 확인했다.
[RAG 원 논문](https://arxiv.org/abs/2005.11401)과 [pgvector의 hybrid 검색 안내](https://github.com/pgvector/pgvector#hybrid-search)도 참고했다. 일반 조사에 임베딩/벡터 검색이 항상 필요한 것으로 해석하지 않는다.
기존 선별 감사 JSON은 당시 원문 확인 이력으로 보존한다. 새 지침·선택 조건의 검증은 DB 동작이나 실제 에이전트 품질의 증거와 구분한다.

## 2026-10-31 후속 적용: mitam-math

직전 조사에서 .agents/skills의 SKILL.md 54개 본문을 확인했다. 42개는 새로 읽고, 4개는 동일한 이전 원문을 재사용하고, 8개는 이전 전체 원문과 변경 구간을 대조했다.
.claude/skills의 42개도 비교했으며 28개는 동일하고 14개는 차이를 확인했다. 하위 참조·스크립트 전체 정독을 의미하지 않는다.
파일별 경로·해시·읽기 방법·누락 참조·재현 결과는 [선별 감사 데이터](mitam-skill-audit.json)에 보존했다.
추가로 읽은 참조는 retry-policy, async-patterns, packaging, structured-logging, nfr-checklist, adr-template이다.

| 참고한 스킬 | 이번에 적용한 범용 절차 | 읽는 조건·주요 수정 |
|---|---|---|
| security-review, secure-code-guardian | 처음에는 verify-work/security, 이후 아래 통합 보안 스킬로 이동 | 인증·권한·업로드·비밀값·실행 설정. 고정 쿠키/CSP·제품 결제 코드·자동 보안 도구 설치 제외 |
| source-command-python-review, test-master | verify-work/review | review 종류/주제. 요구 충족과 결함/회귀를 구분하며 스타일에 따른 고정 심각도·커버리지 강제 제외 |
| strategic-compact | plan-project/handoff와 인수인계 템플릿 | handoff/resume. 목표·결정·실패 조건·근거·다음 행동을 보존. 미검증 hook/세션 제어 이식 제외 |
| source-command-learn-eval, continuous-learning-v2 | plan-project/learning과 학습 기록 템플릿 | learning. 적용/제외 조건·실증·프로젝트/공통 범위. 자동 수집·모델 점수 기반 승인·전역 승격 제외 |
| architecture-designer의 NFR/ADR 참조 | plan-project/quality-requirements와 개요 확장 | plan 종류/quality. 필요한 품질 기준만 선택. 예시 규모·지연·가용성 값을 기본 요구로 쓰지 않음 |
| monitoring-expert의 structured-logging | python-backend/observability | observability 또는 Python 로깅 경로. 최소 상관 정보·비밀값 제외·수명. 전체 관측 스택 설치 제외 |
| ai-api-scaffold의 retry-policy, cost-aware-llm-pipeline | python-backend/external-calls | external-api/llm/streaming. deadline·재시도 중첩·출력 이후 실패·동시성·비용 구분. 최저가 모델 우선·제공자/가격 고정 제외 |

기존 스킬 7개의 조건별 참조를 보강했고 별도 역할 페르소나를 대량 추가하지 않았다.
프로젝트 context.rules는 경로 외에 작업 종류/주제로도 실제 문서를 읽도록 확장했다. 조건은 OR이며 프로젝트 주제는 해당 프로필에 한정한다.
원본의 6개 스킬에서 자기 폴더의 references/*.md 36개가 없었다. 누락 참조를 존재하는 절차로 표현하지 않고 필요한 본문을 새로 작성했다.
문서의 비동기 worker 예제 종료 누락과 WebSocket dataclass의 set 삽입 오류는 격리된 작은 재현으로 확인했다. 원본 서비스의 결함을 판정한 것은 아니며 예제 코드는 복제하지 않았다.

보안 지침은 [OWASP 권한](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html), [업로드](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html), [SSRF](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html), [로깅](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)을 대조해 재작성했다.
검사 경로·읽기 규칙은 자동 테스트로 확인하지만 실제 에이전트 성공률·앱 보안 인증을 증명하는 것은 아니다.

## 2026-10-31 세션 격리·동시 변경 추가 조사

접근 가능한 사용자 홈의 레포·전역 도구 설정을 파일명/경로와 관련 내용으로 탐색했다.
Git 메타데이터 위치 68곳에는 worktree·캐시 복제본도 포함되므로 서로 다른 프로젝트 68개를 정독했다는 뜻은 아니다.
관련 내용 검색 후보는 236개이며 전부 본문을 읽은 것은 아니다. 모델/의존성/빌드 산출물·개인 비밀 설정은 제외했고 Library 전체·휴지통·다른 사용자/마운트 전체는 검토하지 않았다.
Claude/Codex 전체 기록 범위의 관련 원문도 대조했고, Claude plans 디렉터리는 없었다.

| 확인한 자료 | 실제 확인한 기능·한계 | 범용 반영 |
|---|---|---|
| mitam-math의 Git worktree 등록 | 메인 외 별도 worktree 5개가 실제 등록되어 있음 | 세션별 분리·이미 격리된 공간 재사용 |
| 같은 프로젝트의 concurrent-frontend-session, use-worktree-for-features, worktree-dev-servers 메모리 본문 | 동시 편집 경합 때 재읽기·타 세션 변경 보존·메인 브랜치 전환 방지. 포트/의존성 공유의 실제 함정 | collaboration 참조. 기존 서버 일괄 종료·개인 절대경로·환경/의존성 공유는 이식하지 않음 |
| 관련 Claude 원문 2026-10-30 05:40:09 UTC | 같은 작업 트리에 다른 세션의 미완성 변경이 섞여 있어 전체 staging 대신 변경 범위와 정확한 대상 검증이 필요하다고 판단한 기록 | 양쪽 의도·범위 기록과 합친 결과 검증. 과거 기록을 새 실행 권한으로 쓰지 않음 |
| mitam-math의 session-start.js 본문·session-manager.js 관련 구간/함수 검색, 전역/레포 settings의 hooks | 앞선 요약 로딩·세션 기록 관리. 확인한 전역/프로젝트/local 설정의 hooks는 비어 있음 | 이름이 session이라는 이유로 격리/자동 병합 기능이라고 표현하지 않음 |
| sketch-kit의 hooks.json·post_edit_guard.py·stop_guard.py 본문 | 편집/종료 때 debug/secret 유사 패턴 경고. 실행 신뢰 기록과 실제 호출 성공은 별개 | 가벼운 검사와 의미상 통합 검토를 구분. 해당 hook은 설치하지 않음 |
| rivendell의 rv-start.sh·rv-verify.sh·verify.sh 관련 핵심 구간 | 선택적인 worktree 생성·작업 검사·review/merge 안내. 최종 병합을 자동 의미 판정하지 않음 | workspaces.py를 범용 Python 도구로 새로 작성. 승인 단계 강제·manifest 자동 이동·macOS 전용 sed·자동 브랜치 전환 제외 |
| Superpowers 캐시의 using-git-worktrees·finishing-a-development-branch 관련 구간 | 기존 격리 감지·병합 후 검사 절차. 캐시 존재와 활성화는 다르며 현재 Codex enabled plugins 목록에 Superpowers가 없음 | 기존 격리 재사용 원칙 참고. 자동 설치·자동 commit·선택 메뉴 강제·삭제/전역 경로 정책 제외 |

확인한 후보에서 모든 세션의 의미상 충돌을 자동 판단·해결하는 범용 장치를 발견하지 못했다.
현재 하네스에는 checkpoint/run_at과 session/integration 도구를 추가했다. 텍스트 충돌·입력 변경·실제 통합 검사는 도구가 다루고, 요구·의도·설계 판단은 에이전트 절차와 review 기록으로 수행한다.
원본 레포·개인 전역 설정·다른 세션의 worktree는 수정하거나 실행하지 않았다.

## 무엇을 가져왔는지

### 2026-10-31 보안 집중 검토와 통합

사용자가 원하는 범위는 GitHub/CI가 아닌 로컬 설계·구현·외부 응답·의존성·실제 부정 테스트와 수정 검증이다.
이에 맞춰 보안 설계/구현/리뷰 페르소나를 여러 개 복제하지 않고 [security-review](../../../.agents/skills/security-review/SKILL.md) 하나로 통합했다.
기존 verify-work/references/security.md의 책임을 새 스킬의 application/harness 참조로 옮기고 기존 파일과 선택 조건을 제거했다.
공통 경계는 AGENTS, 상세 절차는 스킬 참조, 제품 사실은 프로젝트 security.md, 실행 기능은 tools/harness가 담당한다.

아래는 실제 읽은 원문과 재현 범위다. 다른 레포를 수정하거나 원본 앱·원격 서버에 공격 테스트를 실행하지 않았다.

| 원본 | 확인한 내용·제한 | 반영/제외 |
|---|---|---|
| mitam-math .agents/skills/security-review/SKILL.md 전체, .claude 대응본 비교 | 인증·권한·입력·비밀값·결제·의존성 항목. 업로드 예제의 브라우저 검증, CSP unsafe-inline/unsafe-eval, SameSite 고정, 제공자 서명 예제는 범용 복사에 부적합 | 원칙을 독립 재작성. 서버 검증·프로젝트별 정책·제공자 현재 공식 규격 확인으로 교체 |
| mitam-math security-reviewer·secure-code-guardian SKILL.md 전체 | 각각 연결된 참조 6개·5개가 실제로 없음 | 이름/페르소나와 누락 링크를 복제하지 않고 존재하는 상세 참조 6개 작성 |
| mitam-math security-scan SKILL.md 및 .claude 차이 | Codex 파일 경로를 기계적으로 바꾼 부분과 자동 설치/fix/모델 실행 제안. 현재 하네스 지원 검증 없음 | 자동 전역 설치·미검증 AgentShield·다른 모델 실행 도입 제외 |
| mitam-math common/python/typescript-security 규칙·보안 reviewer agent 전체 | 비밀값·입력·권한 원칙. 도메인/특정 제공자·고정 모델·과도한 도구 권한 포함 | 범용 원칙만 재작성. 고정 권한·모델·제품 정책 제외 |
| mitam-math pre-push-secret-scan.js 전체·등록 파일 | 도구 미설치와 일부 입력/실행 오류가 성공으로 끝날 수 있음 | 빈 임시 디렉터리·격리 PATH에서 missing gitleaks/invalid input의 exit 0을 재현. hook 활성 상태와 전체 실제 이벤트 호출은 검증하지 않음 |
| mitam-math verification-loop 전체 | 일부 확장자만 보는 문자열 검색·head 파이프는 완전한 secret 검사 근거가 아님 | 값 미출력·실제 종료 코드·0개/누락 별도 상태. 제한된 내장 패턴 검사의 한계 명시 |
| mitam-math test-master 전체·WebSocket security 참조 전체·auth-supabase 참조 전체 | 실제 API/메시지/방 권한과 부정 사례. test-master 보안 테스트 참조도 누락 | 실제 처리 경계의 정상/거부/오류/경합 테스트로 연결. 특정 제공자·서비스 내용 제외 |
| sketch-kit AGENTS 관련 보안/프라이버시·hook 구간, security.toml·hooks.json·세 guard 코드 전체 | 독립 앱 보안 스킬은 없음. 읽기 전용 reviewer 설정과 regex hook 존재 | 실제 runtime 호출 검증 없이 지원/강제라고 하지 않음. hook 설치 제외 |
| sketch-kit post_edit_guard의 변경 파일 수집 | unstaged diff 중심으로 untracked/staged 파일 누락 | 원본 함수를 메모리에서 로드하고 임시 Git에서 untracked=False, staged=False, unstaged=True 재현. 새 검사는 tracked+untracked와 explicit 로컬 파일을 지원 |
| sketch-kit github-actions-ci-cd SKILL·workflow-policy 전체, mitam-math frontend workflow 관련 검사 | 최소 권한 등 원칙 참고. mitam의 npm audit는 continue-on-error로 정보성 | 사용자 범위에 따라 CI/CD·배포·GitHub 연결 도입 안 함 |

추가로 mitam-math Docker 보안 구간, sketch-kit backend 보안 테스트의 사례 이름을 확인했다.
FastAPI 전체 본문·일부 backend/deployment 자료는 출력 일부만 확인한 구간이 있으므로 이번 전체 정독 목록에 넣지 않는다.
기존 원본 경로·개인 환경은 출처 식별용이며 실행 의존성이 아니다.

공식 원문과 다음 부분을 대조했다. 확인 시점 이후 제품 API·CLI는 실제 적용 버전에서 다시 확인한다.

- [OpenAI security-best-practices](https://github.com/openai/skills/blob/main/skills/.curated/security-best-practices/SKILL.md), [security-threat-model](https://github.com/openai/skills/blob/main/skills/.curated/security-threat-model/SKILL.md): 보안 검토와 코드에 근거한 위협 모델을 작업 조건에 맞게 사용.
- [OpenAI Agents SDK AGENTS](https://github.com/openai/openai-agents-python/blob/main/AGENTS.md): 도구 출력의 신뢰 경계·합성 데이터·비밀값 취급 참고.
- [Anthropic security-review](https://github.com/anthropics/claude-code-security-review): PR 의미 검토 사례이며 신뢰 불가 입력의 안전한 sandbox라고 볼 수 없음. 실행기를 이식하지 않음.
- [GitHub Agentic Workflows architecture](https://github.github.com/gh-aw/introduction/architecture/): 프롬프트와 별도로 실행·네트워크·출력 권한을 다루는 구조 참고. 이 하네스에 해당 격리가 구현됐다고 주장하지 않음.
- [OWASP AI 개발](https://cheatsheetseries.owasp.org/cheatsheets/Secure_Coding_with_AI_Cheat_Sheet.html), [위협 모델](https://cheatsheetseries.owasp.org/cheatsheets/Threat_Modeling_Cheat_Sheet.html): 입력/도구 신뢰·의존성·검증 경계 반영.
- [Toss webhook 원문](https://docs.tosspayments.com/reference/using-api/webhook-events): 실제 서명 헤더·전송 시각·payload 구성은 로컬 원본 스킬 예제와 차이가 있어 복사 제외. 현재 제품에 결제 기능은 구현하지 않음.
- [npm audit](https://docs.npmjs.com/cli/v11/commands/npm-audit/), [pip-audit](https://github.com/pypa/pip-audit): 진단과 fix/설치 분리, 메타데이터 외부 전송, 종료 코드와 입력 지원 범위를 명시.

전역 시스템 skill-creator의 작성 원칙을 참고했지만 해당 파일을 실행 의존성으로 연결하거나 전역 디렉터리를 복제하지 않았다.
레포 안의 [스킬 관리](skill-authoring.md), doctor와 source-only 포터빌리티 검사로 관리 방법을 남겼다.

실제 하네스 코드 검토에서는 기존 MCP probe의 요청 ID 미대조와 크기 없는 SSE readline을 확인했다.
이를 제한된 chunk 읽기·엄격한 JSON/RPC/ID 확인·HTTPS/리다이렉트/session 검증으로 바꾸고 악성 응답·notification·과대 입력을 로컬 fixture로 시험했다.
공식 [MCP HTTP](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports)와 [lifecycle](https://modelcontextprotocol.io/specification/2025-03-26/basic/lifecycle)을 대조했으며 현재 probe는 2025-03-26과 첫 도구 목록 페이지만 지원한다고 명시했다.
원격 도구가 실제 제품에서 안전하게 작동한다는 검증과는 다르다.
또한 소스 아카이브 순회 중 읽을 수 없는 디렉터리를 조용히 생략하지 않도록 공통 파일 열거의 오류를 전파한다.

### 2026-10-31 E2E 후속 보완

mitam-math의 e2e-testing·playwright-expert·source-command-e2e에서 사용자 흐름 선택·독립 데이터·실행·실패 artifact 분석 절차를 참고해 독립 [e2e-testing](../../../.agents/skills/e2e-testing/SKILL.md) 스킬을 추가했다.
앞선 적용에서는 browser 참조에 일부 원칙만 반영했으므로 E2E 절차를 충분히 이식했다고 볼 수 없었다.
이 단계에서는 스킬 8개였으며 UI/E2E 경로·주제에서 읽도록 연결했다. 이후 보안 통합으로 9개가 됐다. Playwright config/시나리오 템플릿과 프로젝트 로컬 runner→새 JUnit을 연결하는 실행기도 추가했다.
원본의 제품 결제/교육 시나리오·개인 설정·강제 병렬화/POM·불안정 테스트 자동 skip은 가져오지 않았다.
이 절차와 템플릿은 실제 앱별 서버·데이터·테스트를 등록할 때 사용한다. 아직 없는 앱의 E2E가 실행됐다는 의미는 아니다.

| 원본 레포·자료 | 채택한 부분 | 반영 위치·수정 |
|---|---|---|
| zero-error-claude-package: search-first | 레포 검색 후 채택/확장/직접 구현 비교 | research/reuse. 강제 연구 에이전트·개인 설정 경로 제외 |
| 같은 레포: iterative-retrieval | 부족한 경계에 따라 검색어·원문을 확장 | plan-project/context-retrieval. 고정 3회·점수/파일 수 기준 제외 |
| 같은 레포: eval-harness | 요구 기준 사전 정의·능력/회귀 평가·평가기 구분 | experiment/harness-evaluation, 평가 사례. 특정 도구 명령·고정 성공률 제외 |
| 같은 레포: verification-loop | build·types·lint·tests·diff의 서로 다른 역할 | verify-work. 매번 전부 실행·15분 주기·일괄 80% 기준 제외 |
| 같은 레포: python-patterns | 명시적 경계·타입·예외 원인·context manager | python-backend/structure, resources. 기초 문법 매뉴얼·버전 조합·불필요 최적화 예시 제외 |
| 같은 레포: python-testing | fixture 격리·경계값·parametrize·적절한 mock | python-backend/testing. Flask 예제를 FastAPI 예제로 부르는 부분·일괄 TDD/커버리지 강제 제외 |
| 같은 레포: api-design | status·오류·소유권·중복·pagination의 계약 | python-backend/api-contracts. 고정 envelope·버전 경로·도메인 분석 API 제외 |
| 같은 레포: database-migrations | 기존 소비자·데이터 호환·단계적 변경을 고려 | verify-work/impact, API 계약의 영향. DB 미정이므로 SQL·특정 DB·실행 명령은 이식하지 않음 |
| 같은 레포 및 mitam-math: e2e-testing·playwright-expert·source-command-e2e | 의미 locator·상태 대기·독립 데이터·실행·실패 artifact | e2e-testing과 verify-work/browser. networkidle 기본 대기·동작 뒤 대기 등록·강제 POM/병렬화 제외 |
| mitam-math: frontend-patterns | runes·context·데이터/폼·구독 수명·UI 상태 | svelte-frontend의 참조 3개. 교육 도메인 제거, SSR 공유 상태·응답 경합·불완전 정리 예제 보완 |
| mitam-math: fastapi-expert 및 lifespan/testing/error 참조 | 기능 응집·앱 factory·자원 수명·DI·API 테스트 | python-backend의 참조 4개. FastAPI/DB/Redis 강제·빈 파일 세트 제외 |
| zero-pod: verify-before-commit | 정확한 index 사본·누락 파일·stale 근거 | verify-work/evidence와 기존 staged 실행기 유지. 요청 없는 staging·커밋 메시지 차단 규칙 제외 |
| sketch-kit: design-system-first 및 계약/권위/UI 검증 참조 | 승인 기준·토큰 계층·props/상태·주변 화면 비교 | design-first/contracts, svelte UI 계약. React·제품 규격·사소한 변경별 재승인 제외 |
| sketch-kit: github-actions-ci-cd | 실제 명령 기반 CI·최소 권한·필수 check 상태 | verify-work/ci. 배포/runner 자동 도입 제외. 부속 workflow-policy는 이번 전체 읽기 목록에 포함하지 않음 |
| math-ilta-svelte: DESIGN.md | 코드 기반 인벤토리·토큰→컴포넌트→화면·실제 데모 연결 | design-first/contracts. 브랜드 값·서체·Figma 키·도메인 원자 목록 제외 |
| stt-tts: research-method 규칙 | 주장 장부·출처 독립성·반증·정확한 변종·실측 구분 | research/evidence, experiment/protocol. 특정 모델/구독·공동 모델 강제·고정 검색 횟수 제외 |
| spec-kit-test: tasks-template | 독립 확인 가능한 사용자 기능·의존성·점진 구현 | plan-project/task-patterns. 모든 기능 전 공통 인프라 강제·방대한 필수 문서·자동 배포 제외 |

이 레포의 실행은 Codex만 사용한다. 과거 다른 도구 이름이 들어간 원본 경로는 출처일 뿐 실행 설정으로 복원하지 않는다.
원본에 metadata license가 있는 것과 레포 전체/부속 파일의 재배포 권한이 확인된 것은 구분한다.
대량 복제·원본 설치기를 실행하지 않았고, 사용자 데이터·개인 설정·권한 예외는 옮기지 않았다.

## 그대로 가져오지 않고 고친 예

1. 타이머 취소만으로 이미 시작한 검색 요청이 취소된다고 가정하지 않는다. 요청 취소와 오래된 응답 무시를 함께 설명했다.
2. 서버의 사용자별 모듈 상태를 범용 공유 상태 예제로 쓰지 않는다. 요청/트리 범위를 분리했다.
3. 자원 초기화 후 yield 아래 정리 코드만 두는 예제를 그대로 쓰지 않고, 중간 시작 실패에도 정리할 수명을 설명했다.
4. AsyncClient+ASGITransport만으로 lifespan이 실행됐다고 하지 않는다.
5. 응답을 기다리는 코드를 클릭 뒤 등록하거나 networkidle을 준비 상태로 고정하지 않는다.
6. head/tail 파이프 뒤의 코드로 검사를 판정하거나 secret grep 결과를 출력하지 않는다. 실제 프로세스와 보존 로그를 사용한다.
7. pytest/Vitest를 종료 코드만으로 통과시키지 않도록 새 JUnit 보고서 경로와 0개/skip/실패 판정을 추가했다.

## 공식 원문으로 다시 확인한 부분

- SSR 사용자 상태 경계: [SvelteKit 상태 관리](https://svelte.dev/docs/kit/state-management)
- 효과·정리·의존성: [Svelte $effect](https://svelte.dev/docs/svelte/$effect)
- 앱 시작/종료: [FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/), [Python AsyncExitStack](https://docs.python.org/3/library/contextlib.html#contextlib.AsyncExitStack)
- 비동기 API 테스트 수명: [FastAPI async tests](https://fastapi.tiangolo.com/advanced/async-tests/)
- 테스트 출력: [pytest JUnit](https://docs.pytest.org/en/stable/how-to/output.html), [Vitest reporters](https://vitest.dev/guide/reporters.html)
- 화면 준비 상태: [Playwright waitForLoadState](https://playwright.dev/docs/api/class-page#page-wait-for-load-state)

확인일은 위 날짜다. 프레임워크 API를 실제 프로젝트에 적용할 때는 잠금 버전에 맞춰 다시 확인한다.

## 첫 보강의 확인 범위와 한계

원본의 모든 부속 파일을 읽은 것은 아니다. 아래 목록이 이번 전체 본문 확인 범위다.
이전 조사에서 제목·일부 구간만 본 다른 스킬을 이번 선별 완료 목록에 넣지 않았다.
구체적인 파일 목록·줄 수·해시 접두사를 아래에 기록해 이후 원본 변경과 구분한다.

| 원본 레포 | 상대경로 | 줄 수 | SHA-256 접두사 |
|---|---|---|---|
| zero-error-claude-package | `skills/search-first/SKILL.md` | 161 | `752b24a8a06b3df1` |
| zero-error-claude-package | `skills/iterative-retrieval/SKILL.md` | 211 | `5bf02488afe55042` |
| zero-error-claude-package | `skills/eval-harness/SKILL.md` | 236 | `0bc29828b0b20c57` |
| zero-error-claude-package | `skills/verification-loop/SKILL.md` | 127 | `32178b774c16b7f4` |
| zero-error-claude-package | `skills/python-patterns/SKILL.md` | 742 | `31839955de8d90e6` |
| zero-error-claude-package | `skills/python-testing/SKILL.md` | 816 | `b304a8c503af3264` |
| zero-error-claude-package | `skills/e2e-testing/SKILL.md` | 324 | `0f9c93d6c916aeb5` |
| zero-error-claude-package | `skills/playwright-expert/SKILL.md` | 80 | `40c693a631a8800a` |
| zero-error-claude-package | `skills/api-design/SKILL.md` | 486 | `07b6f254b92f12a7` |
| zero-error-claude-package | `skills/database-migrations/SKILL.md` | 346 | `6c06e01f28f327d4` |
| mitam-math | `.agents/skills/frontend-patterns/SKILL.md` | 2067 | `83b4c71b618b3e10` |
| mitam-math | `.agents/skills/fastapi-expert/SKILL.md` | 532 | `ff3d2a72af537bab` |
| mitam-math | `.agents/skills/fastapi-expert/references/lifespan-clients.md` | 156 | `b621122577d079f2` |
| mitam-math | `.agents/skills/fastapi-expert/references/testing-async.md` | 159 | `2d7beed8296510fa` |
| mitam-math | `.agents/skills/fastapi-expert/references/testing.md` | 113 | `d4cbbe3d2710fa11` |
| mitam-math | `.agents/skills/fastapi-expert/references/error-handling.md` | 82 | `79363143abb05109` |
| zero-pod | `.agents/skills/verify-before-commit/SKILL.md` | 63 | `6d6c0ec0b1a120f7` |
| sketch-kit | `.agents/skills/design-system-first/SKILL.md` | 132 | `83bab9f2734ce90c` |
| sketch-kit | `.agents/skills/github-actions-ci-cd/SKILL.md` | 91 | `8714c8fef0110067` |
| sketch-kit | `.agents/skills/design-system-first/references/component-contracts.md` | 282 | `b9ae5d1af337c9d7` |
| sketch-kit | `.agents/skills/design-system-first/references/design-authority.md` | 87 | `57910b5151e3edb2` |
| sketch-kit | `.agents/skills/design-system-first/references/ui-verification.md` | 82 | `9098cf36048dbb54` |
| stt-tts | `.claude/rules/research-method.md` | 153 | `4869d4785d3f75b3` |
| math-ilta-svelte | `src/lib/components/DESIGN.md` | 269 | `7ac24ba1aa3e558e` |
| spec-kit-test | `.specify/templates/tasks-template.md` | 251 | `5da92ac1fbf5be2f` |

## 2026-10-31 검증 실행·증거·실험 보강

이번 단계는 새 스킬 수를 늘리는 대신 verify-work의 완료 참조, experiment의 실행/평가 연결,
plan-project의 종류별 완료 기준을 실제 도구와 연결했다. 기존9개 스킬을 유지한다.

| 참고한 원문/도구 | 가져온 원칙과 반영 위치 | 그대로 가져오지 않은 것 |
| --- | --- | --- |
| sketch-kit의 post_edit_guard.py·stop_guard.py와 .codex/hooks.json | 변경/완료 시 놓친 경계를 확인한다는 취지 → 실제 검사 선택·증거 해시·완료 리뷰 | hook 이벤트 지원을 검증하지 않은 설정 복사, 경고만으로 자동 보호라고 주장 |
| mitam-math의 동시 frontend 세션·worktree 사용 메모, session-manager/session-start | 다른 세션 변경 보존·격리·인수인계 → 기존 workspaces와 완료 기록 연결 유지 | 개인 경로·환경 symlink·서버 전체 종료·기록 도구를 자동 의미 병합으로 해석 |
| [SvelteKit CONTRIBUTING](https://github.com/sveltejs/kit/blob/main/CONTRIBUTING.md) | 검사 종류와 관련 실행 범위 구분 → 기존 checkpoint 유지·Make 실제 동작 회귀 | 매 편집마다 전체 통합 검사/반복 stress |
| [FastAPI template Playwright](https://github.com/fastapi/full-stack-fastapi-template/blob/master/.github/workflows/playwright.yml) | 범위 선별·불안정 결과와 실패 증거 취급 → JUnit flaky 집계·원본 무결성 | GitHub 연결·CI·shard·서비스 프레임워크 강제 |
| [Python3.12 subprocess](https://docs.python.org/3.12/library/subprocess.html) | root timeout과 session API 구분 → bounded Popen·group 정리·권한 거부 실패 | 임의 코드 실행 sandbox 또는 모든OS 동등성 주장 |
| [MLflow Tracking](https://mlflow.org/docs/latest/ml/tracking/)·[DVC experiments](https://doc.dvc.org/user-guide/experiment-management) | 실행별 설정·입력·원본·지표·전체 실패를 기록해 조건 일치 비교 | 추가 서비스/패키지 설치·파일 포맷 호환·분산 실행 |
| [JOSS review criteria](https://joss.readthedocs.io/en/latest/review_criteria.html) | 핵심 기능이 실제로 확인되는 근거 → 종류별 증거와 기준별 리뷰 | 논문 제출·오픈소스 공개·GitHub 운영 요건 |

로컬 원문은 필요한 파일/관련 구간을 읽은 범위이며 노트북의 모든 레포·모든 세션 전체를 본문 정독했다는 뜻은 아니다.
외부 텍스트/코드를 대량 복사하지 않고 로컬·범용·현재 사용자 제약에 맞춰 재작성했다.
결정적 도구 검사·알려진 답의 파일럿과 실제 독립 에이전트 품질 비교를 [평가 문서](harness-evaluation.md)에서 구분한다.
