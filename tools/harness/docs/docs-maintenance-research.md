# 문서 관리·LLM Wiki 스킬 도입 조사

확인일: 2026-10-31. 사용자가 문서 정리 스킬과 그 하위 위키 기능을 요청했고, 공개 사례 조사와 로컬 통합 검토를 서브에이전트 3개로 병렬 진행했다.
아래 내용은 접근 가능한 공개 원문을 읽고 이 레포에 맞춰 종합한 설계다. 사례 수·인기·문서량은 효과나 보급률의 증거로 사용하지 않는다.

## 결과와 책임

[docs-maintenance](../../../.agents/skills/docs-maintenance/SKILL.md)는 문서 구조·최신화·위키·검증을 한 스킬의 작업 모드로 제공한다.
본문은 공통 경계와 읽기 조건, 참조 4개는 실제 절차다. 실제 프로젝트 지식을 이 폴더에 저장하거나 빈 위키를 미리 생성하지 않는다.
직접 작성한 한국어 절차이며 외부 스킬·코드의 설치나 전문 복제를 하지 않았다.

| 책임 | 담당 |
|---|---|
| 질문 조사·검색·근거 판정 | 기존 research |
| 제품 요구·결정·진행 상태·인수인계 | 기존 plan-project와 프로젝트/작업 문서 |
| 재사용할 정정·해결의 범위·채택 상태 | 기존 learning 절차와 현재 knowledge 도구 |
| 문서 배치·동기화·출처 기반 주제 종합 | 새 docs-maintenance |
| 검사 실행·요구 대조·완료 근거 | 기존 verify-work와 등록된 로컬 도구 |

## 공개 스킬에서 확인한 구성

| 원문 | 확인한 장점과 이번 반영 | 그대로 이식하지 않은 조건 |
|---|---|---|
| [OpenAI Agents Python docs-sync](https://github.com/openai/openai-agents-python/blob/main/.agents/skills/docs-sync/SKILL.md) | 문서→코드와 코드→문서의 양방향 대조, 범위 기반 기능 목록, 생성 문서는 입력부터 수정, 변경별 검증 | 영어만 편집·특정 SDK 경로·특정 빌드 명령·개별 worktree 승인 정책은 해당 레포의 조건 |
| [Pipecat update-docs](https://github.com/pipecat-ai/pipecat/blob/main/.claude/skills/update-docs/SKILL.md) | 공통 절차와 프로젝트별 매핑/스타일 분리, 실제 경로 확인, 기본값·제약·예외·폐기 설명과 파생 가이드 대조, 정확한 문장 보존 | docs.json·별도 docs 레포·main 고정·자동 branch/commit/PR. 코드가 현재 사실이어도 승인된 제품 의도까지 덮지 않음 |
| [Hugging Face OpenEnv update-docs](https://github.com/huggingface/OpenEnv/blob/main/.claude/skills/update-docs/SKILL.md) | API 변경 목록을 docs·예제·docstring에 전파하고 최소 변경 관점에서 재검토 | Python/API signature만으로 영향 한정, HEAD~1 고정, 특정 agent/hook 의존 |
| [TanStack AI docs](https://github.com/TanStack/ai/blob/main/.claude/skills/docs/SKILL.md) | 독자·목표·인접 문서 관례 확인, 실제 질문/여정 단위로 분리 | persona/tone마다 정지 승인, 개인 스킬 의존, 고정 글자 수·목록 개수 기준 |
| [tomzx sync-documentation](https://github.com/tomzx/agents/blob/main/skills/sync-documentation/SKILL.md) | API·설정·예제·navigation·링크·빌드의 drift 분류, 검출/수정 상태 구분. 외부 링크는 원문도 보고만 함 | HEAD 비정상 응답의 broken 판정·nav 자동 수정은 근거와 요청에 따라 판단. docs 부재 시 사이트 구축 권고는 기본 절차에 넣지 않음 |
| [drvoss doc-update](https://github.com/drvoss/everything-copilot-cli/blob/main/skills/documentation/doc-update/SKILL.md) | 코드 대조→대상 수정→예제·링크 검증의 작은 반복을 비교 참고 | 수정일 비교만으로 노후 판정, 최신 npx 도구 설치, changelog 자동 확대. 라이선스 원문 미확인으로 직접 복제 제외 |

이 표는 사용자 범위·승인된 의도·병렬 작업·로컬 재현을 우선하도록 조정한 결과다.
관측한 구현과 승인 요구가 충돌하면 구현 결함/문서 오기/미확정 결정을 분류하고, 문서만 구현에 맞춰 수정해 요구를 낮추지 않는다.

## 위키 원문에서 확인한 구성

| 원문 | 반영한 절차 | 기본 기능으로 채택하지 않은 범위 |
|---|---|---|
| [Karpathy LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) | 원본·파생 위키·운영 규칙 분리, ingest/query/lint, 주제 종합·인덱스·변경 이력 | 특정 폴더/도구를 필수화하거나 자동으로 사실이 검증된다는 해석 |
| [nvk wiki-manager](https://github.com/nvk/llm-wiki/blob/master/claude-plugin/skills/wiki-manager/SKILL.md), [ingestion](https://github.com/nvk/llm-wiki/blob/master/claude-plugin/skills/wiki-manager/references/ingestion.md), [linting](https://github.com/nvk/llm-wiki/blob/master/claude-plugin/skills/wiki-manager/references/linting.md) | 자료 중복·버전 확인, 원본 보존·증분 처리, 인덱스와 실제 문서 대조, 공백 표시 | 전역 hub·topic registry·iCloud·portfolio·private adapters·세션 캡처·specialist factory |
| [praneybehl llm-wiki](https://github.com/praneybehl/llm-wiki-plugin/blob/main/skills/llm-wiki/SKILL.md), [ingest](https://github.com/praneybehl/llm-wiki-plugin/blob/main/skills/llm-wiki/references/ingest-workflow.md), [lint](https://github.com/praneybehl/llm-wiki-plugin/blob/main/skills/llm-wiki/references/lint-workflow.md) | 스킬/지식 저장 범위 분리, 인덱스→관련 본문, 기존 주제 우선·부분 편집·원본 재확인 | 고정 줄/페이지 임계값, embedding/graph DB 설치 의무, 모든 수정의 재승인, SCHEMA를 현재 사용자 지시 위에 두는 해석 |
| [Paperclip wiki-lint](https://github.com/paperclipai/paperclip/blob/master/packages/plugins/plugin-llm-wiki/skills/wiki-lint/SKILL.md) | 모순·노후·고립·개념 공백·깨진 링크·순환 인용·이력 불일치를 위치/근거/영향/조치로 분류 | plugin issue/wikiId/spaceSlug/MCP 의존. 원문의 lint도 log 쓰기가 있어 완전 읽기 전용이라고 일반화하지 않음 |

추가로 [hjhun wiki-lint](https://github.com/hjhun/llm-wiki/blob/main/.agents/skills/wiki-lint/SKILL.md)와 [harrylabsj runtime README](https://github.com/harrylabsj/llm-wiki-karpathy-plugin/blob/main/README.md)를 비교했다.
두 곳은 라이선스 원문을 확인하지 못해 문구/코드 복제 후보에서 제외했다. hosted runtime은 현재 절차에 필요한 의존성이 아니다.
위키 질문만 요청하면 읽고 답하며 저장하지 않는다. 반영 요청 안에서는 확정 가능한 편집을 수행하고 새 정책 결정은 임의로 확정하지 않는다.

## 공식 문서로 보강한 기준

| 근거 | 반영 | 이식하지 않은 레포별 정책 |
|---|---|---|
| [Diataxis compass](https://diataxis.fr/compass/) | 학습·문제 해결·정확한 조회·배경 이해의 목적 구분 | 네 폴더/문서 의무 생성 |
| [Google Technical Writing: Documents](https://developers.google.com/tech-writing/one/documents) | 독자·목표·범위·전제와 논리적인 읽기 순서 | 작은 수정마다 장문의 audience/scope 문서 작성 |
| [Google code samples](https://developers.google.com/style/code-samples) | 예제 설명·언어별 코드 관례·생략 표시, 완전 실행 예제와의 구분 | 모든 언어의 들여쓰기·줄 길이를 일괄 고정 |
| [GitLab workflow](https://docs.gitlab.com/development/documentation/workflow/) | API·사용자·운영 변화와 문서 영향, 기술 정확성 검토 | 역할별 승인·MR·CI 절차 |
| [GitLab testing](https://docs.gitlab.com/development/documentation/testing/) | Markdown·앵커·생성·빌드의 검사 층 구분 | 새 사이트·Vale·markdownlint·CI 일괄 설치 |
| [GitLab redirects](https://docs.gitlab.com/development/documentation/redirects/) | 이동/병합 시 inbound links·게시 URL·목적지 안내 확인 | 특정 frontmatter·redirect 보존 기한 |

## 실제 스킬에 반영한 기능

- organization: 문서 지도·독자/목적·정본·중복 판단, 병합/분할/이동의 내용 대응과 링크/앵커/navigation, 현재/과거 구분, 읽기 흐름·용어·예제.
- synchronization: 범위·버전·권위 구분, 코드/결정과 양방향 대조, 기본값·오류·권한·복구, 생성 입력·번역·미출시 구분.
- wiki: 원본과 파생 자료 분리, 중복 회피·증분 갱신·출처/시점/버전, 모순·정정·공백, 질문·lint, 순환 인용·자료 속 지시문의 권한 승격 방지.
- validation: 변경별 검사, 내용 보존과 주장을 지지하는 근거 확인, 링크/앵커/렌더링의 검사 한계, 명령의 부작용 판단, 실제 실행/미실행 구분.

상세 자료는 해당 주제에서만 읽는다. `docs`는 진입점, `docs-organization`·`docs-sync`·`wiki-query`·`docs-check` 등은 해당 참조로 연결된다.
일반 `knowledge-base`/RAG 조사에는 위키 쓰기 절차를 자동 추가하지 않는다. 문서 경로가 맞으면 진입점만 선택되고 다음 절차는 실제 요청에서 고른다.
프로젝트 위키의 다음 세션 읽기는 기존 진입점과 workflow의 context.rules로 연결하며 자동 주입/주기 실행을 구현했다고 표현하지 않는다.

## 라이선스·원문 확인 범위

조사 에이전트가 [Pipecat BSD-2-Clause](https://github.com/pipecat-ai/pipecat/blob/main/LICENSE), [OpenEnv BSD-3-Clause](https://github.com/huggingface/OpenEnv/blob/main/LICENSE),
[TanStack MIT](https://github.com/TanStack/ai/blob/main/LICENSE), [tomzx MIT](https://github.com/tomzx/agents/blob/main/LICENSE),
[nvk MIT](https://github.com/nvk/llm-wiki/blob/master/LICENSE), [praneybehl MIT](https://github.com/praneybehl/llm-wiki-plugin/blob/main/LICENSE), [Paperclip MIT](https://github.com/paperclipai/paperclip/blob/master/LICENSE)를 확인했다.
일부 스킬이 연결하는 부속 agent 원문·LICENSE는 웹 접근 실패로 읽지 못했으며, 그 내용은 채택 근거로 삼지 않았다.
위키 gist는 개념 참고이며 명시적인 재배포 라이선스를 확인한 것으로 취급하지 않는다.
문서/코드를 직접 가져올 때는 해당 파일까지 적용되는 조건을 다시 확인해야 한다. 이번 작업은 개념을 종합해 새 절차를 작성했다.

## 검증 범위와 한계

스킬 metadata·참조·등록·내부 링크는 기존 skill validate/doctor로, 읽기 조건은 실제 context 결과로 확인한다.
선택 조건 변경에는 등록된 Python 회귀 검사를 사용하고, 문서 이동·구현 불일치·상충 출처 반영의 합성 사례를 별도 로컬 임시 공간에서 수행한다.
형식 통과·합성 사례 결과는 실제 모든 프로젝트에서의 사실 정확성이나 자동 유지 성능을 보증하지 않는다.
이 스킬은 저장/등록한 절차이며 전용 문서 편집 CLI·위키 daemon·정기 작업을 구현한 것이 아니다.
외부 발행·커밋·푸시·배포·원격 수정은 수행하지 않는다.

과거 맥락은 Claude projects/subagents/memory와 Codex sessions/archived/history/index 전체를 검색 범위로 삼고 관련 원문을 확인했다.
이 대화에서 확인한 2026-10-30~31 구조/읽기 결정은 재사용했다. `~/.claude/plans/`는 없으며 공개 사례의 비공개 운영이나 접근 실패한 원문은 확인 범위에 포함하지 않는다.
