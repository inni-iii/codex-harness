# 추가 기능의 전체 연결·문서 점검 결과

2026-10-31. 대상은 추가한 학습·스킬 관리·환경 준비·설정 감사와 이들을 소비하는 전체 레포의 지침/설정/문서/검사다.
수정 전 소스와 실패 보고서를 보존하고 관련 회귀를 통과시킨 뒤 공통 등록 검사로 통합 확인한다. 실제 실행 수·종료 결과·보고서 위치는 같은 작업의 notes.md와 typed evidence에 남긴다.

## 역할과 설명 위치

전체 코드 지도와 사용 계약 연결은 [architecture](../../../tools/harness/docs/architecture.md)를 따른다. 작업별 시작 지도는 [AGENTS](../../../AGENTS.md)다.

| 질문 | 정본과 실제 소비 경로 |
|---|---|
| 무엇을 읽어야 하나 | .agents/context.toml → context.select → 스킬/조건부 참조·프로젝트 자료·현재 증거를 가진 지식. CLI는 원문 읽기 보조이며 Codex 자체의 스킬 발견과 별개다. |
| 무엇을 기억하나 | [maintain-knowledge](../../../.agents/skills/maintain-knowledge/SKILL.md) → knowledge CLI → docs/knowledge/catalog.json. 진행 상황은 task/notes, 재사용 교훈은 catalog에 둔다. 위키는 주제별 출처 종합 자료다. |
| 적용 가능한 규칙인가 | 프로젝트/공통 범위·kind/topic/path OR·증거 해시는 코드가 선별한다. 자연어 conditions/exclusions와 근거 내용의 진위는 에이전트가 판단한다. |
| 언제 자동 실행하나 | .codex/hooks.json → scripts/knowledge-hook.py → knowledge_hooks. SessionStart는 지식 안내, PreCompact/Stop은 제한된 task 메타데이터 기록이다. UserPromptSubmit → route_prompt.py의 분류/작업 인수인계와 구분한다. |
| 어떻게 스킬을 늘리나 | [maintain-skills](../../../.agents/skills/maintain-skills/SKILL.md) → skill create/from-knowledge → SKILL.md/context 등록. 스킬은 판단·작성 절차, [skill-authoring](../../../tools/harness/docs/skill-authoring.md)은 CLI/입력/등록 계약이다. |
| 어떻게 설치하나 | [setup-environment](../../../.agents/skills/setup-environment/SKILL.md) → environment inspect/install → 저장소 선언/lock·고정 설치·결과 해시. 기본 setup은 inspect만 한다. |
| 설정은 어떻게 확인하나 | security-review → security config → 기본 agent-config 검사. 선택적 AgentShield는 별도 CLI 정적 어댑터이며 미설치는 unavailable이다. |

## 발견과 보완

- F1: 학습 훅이 제외 조건을 빠뜨리고 본문/적용 조건을 자른 채 전달했다. 완전한 적용 단위 또는 원문 조회로 바꿨다. 짧은 규칙의 제외 조건 보존·긴 규칙의 부분 지시 미전달을 자동 회귀로 확인한다.
- F2: workflows의 자동 실행 부재 설명, 모든 훅을 학습 훅처럼 설명한 문구, 자연어 조건과 실제 선택 조건의 혼동을 고쳤다. 구조 지도에 catalog·학습 스크립트·선택적 감사기 위치를 보완하고 초기 참고 자료의 읽기 경로도 복구했다.
- F3: 잘못된 state/history.action 자료형이 검증 오류 대신 처리되지 않은 TypeError를 만들었다. 검증 단계에서 일관되게 거부한다.
- F4: import의 저장 용량 검사가 실제 파일보다 작은 compact JSON에 적용돼 읽을 수 없는 catalog를 만들었다. 내보내기에도 같은 한도가 없었다. 실제 들여쓰기·개행·UTF-8 크기를 저장 전에 확인해 기존 catalog와 출력 경로를 보존한다.

F1/F3/F4는 같은 회귀 파일의 수정 전 실패 보고서와 수정 후 보고서를 연결한다. F4의 큰 export도 별도 합성 입력에서 출력 미생성·원본 보존을 확인했다. F2는 수정 전 원문·현재 코드 계약과 수정 후 문서/링크/명령을 대조한다.

## 문서 구조와 중복 판단

- 루트 README는 사용 시작, AGENTS는 공통 지침·작업 지도, .agents는 재사용 절차, tools/harness/docs는 도구의 현재 계약, docs/projects는 제품 사실, docs/tasks는 작업별 근거, catalog는 검토 지식을 담당한다.
- Markdown 전체에서 링크·제목 앵커 후보·긴 동일 문단과 진입 경로를 정적으로 확인하고, 추가 기능과 맞닿는 문서를 실제 구현과 대조했다. task notes는 task 디렉터리/CLI에서 발견되므로 일반 목차에 모두 추가하지 않는다.
- 학습 판단·스킬 절차·CLI 명세는 서로 연결하며 같은 규칙의 별도 정본을 늘리지 않는다. skill-authoring의 반복된 일반 작성 절차를 입력/등록 계약으로 정리했다.
- 초기 구성안·도입 이력·과거 검사 수는 당시 상태를 보존한다. 현재 안내와 연결하며 과거 내용을 현재 구현으로 조용히 바꾸지 않는다.
- 정적 파일/앵커 확인은 브라우저 렌더·외부 URL 가용성·모든 문서 주장의 진실성 검사와 다르다. Markdown과 설정/CLI 작업이어서 제품 브라우저 E2E는 비적용이다.

## 남은 실제 환경 확인

현재 run의 분류용 CLI가 in-process app-server 초기화 권한 오류로 시작되지 않았다. 모델 라우팅 성공이나 독립 작업 모델의 검토로 표시하지 않는다. 수행 가능한 로컬 점검·검사 결과와 구분한다.
AgentShield 실엔진 설치/탐지, Codex 프로젝트·훅 신뢰와 실제 native compact 이벤트는 여전히 미확인이다. 공식 신뢰/실행 절차와 네트워크가 가능한 로컬 환경에서 확인하며 이 감사의 로컬 통과로 대체하지 않는다.
