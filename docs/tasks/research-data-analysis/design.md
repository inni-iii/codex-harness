# research 데이터 분석 절차 보완

```json
{"version":1,"kind":"reasons-design","profile":"behavioral","requirements":["R1","R2","R3","R4"],"operations":[{"id":"O1","requirements":["R1","R2","R3","R4"],"paths":[".agents/skills/research/**",".agents/context.toml",".agents/skill-flow.toml","AGENTS.md","README.md","tools/harness/tests/test_research_data_analysis.py","docs/tasks/research-data-analysis/**"],"depends_on":[],"verification":"공식/원저 읽기·선택/비선택·plan 호출/복귀와 근거 없는 통과 차단·합성CSV/중첩JSON 실제 계산과 원본 보존·doctor 및 관련 등록 검사"}],"decisions":[]}
```

## Requirements

R1 데이터 분석 방법론을 웹의 공식/원저 자료로 비교한다. R2 별도 스킬을 늘리지 않고 research의 데이터 질문·품질·방법·해석·재현 상세 절차로 보완한다. R3 CSV/JSON 실제 합성 반례로 관측 단위/지표별 분모·집단 구성·중첩 합계를 확인한다. R4 선택과 flow·원문/문서 지도를 연결하고 일반 JSON 설정에 분석 절차를 불필요하게 읽히지 않는다.

## Entities

질문·판단·모집단/표본·기간·관측 단위·키·원본 식별자, 지표별 필수 필드/분모, 정제/조인·집계 결과, 방법의 가정·관측/해석/제안, 재현 근거와 한계.

## Approach

PPDAC/CRISP-DM을 질문 규모에 맞게 참고하고 품질·EDA·통계 해석·목적 검증을 조합한다. 단일 만능 모델/검정/데이터 정제법을 고정하지 않는다. pandas 등은 선택 도구이며 새 의존성·파서·분석 엔진·라이브러리 설치를 추가하지 않는다.

## Structure

research SKILL은 적용 조건과 상세 참조 한 개를 연결한다. references/data-analysis.md는 수행 판단·질문별 방법·실패/해석 경계를, assets/data-analysis.md는 필요한 경우 기존 정본에 채울 가벼운 계약을 담당한다. context 주제와 analyze-data 라우트·계획/조사에서의 호출 및 선택적 실험/검토/문서 연결을 등록한다. 일반 *.json 파일 경로를 광범위 trigger로 추가하지 않는다.

## Operations

### O1

현재 요청과 과거 원문·기존 research/experiment를 대조하고 공식/원저를 조사했다. 문서/등록 초안을 격리 공간에 작성했다. 현재 범위와 원문을 정렬 검토한 뒤 정상/오류/비선택·합성 분석을 검증하고 최신 결합 상태에서 통합한다. 분석 보고서의 실제 수치/가정/반례와 행수·원본 해시를 연결한다.

## Norms

기존 원문과 타 세션 변경, 문서 지도/선택 읽기·기능 정본 갱신·요청 범위를 보존한다. 작은 분석마다 새 task/문서 세트를 강제하지 않는다. 외부 문서의 조직 승인·도구 설치·배포를 사용자 지시로 승격하지 않는다.

## Safeguards

원본은 읽기 전용, 공개 검색어만 사용, 비밀/원본 개인정보를 외부로 전송하지 않는다. 미확인 원문·표본·파싱 성공·합성 fixture를 전체 분석/인과/실서비스 성능으로 바꾸지 않는다. 통계 가정과 정제 선택의 적절성은 에이전트가 판단하며 자동 승인하지 않는다. 요구를 바꾸는 미결정만 확인하고 이미 승인한 작은 보완 범위의 세부 승인은 반복하지 않는다.
