# REASONS 설계와 구현 진입

스킬14개를 유지하며 plan-project의 analysis/design/alignment와 docs-maintenance의 intent-update/implementation-sync를 연결한다. 기존 모델 추천 route, call/transition/steps_complete/user_choice/reason 의미는 유지한다.

## 실행 흐름과 책임

`요구/목표 → 분석 → REASONS 설계 → 정렬 검토 → 구현 → 실제 검증 → 필요한 설계/문서·위키·인덱스 갱신`으로 수행한다.
의도/개념·대안·책임·R/O는 [계획 절차](../../../.agents/skills/plan-project/references/reasons-canvas.md), 문서의 권위·변경 방향·정본/인덱스는 [명세 유지](../../../.agents/skills/docs-maintenance/references/specifications.md)를 따른다.
UI 디자인 시스템은 design-first, 세부 구현/보안/검증은 해당 기존 스킬이 맡는다.

현재 Python/Svelte/PostgreSQL 구현, maintain-skills:maintain, verify-work:repair/check는 필수 design/alignment 입력과 entry_checks=["alignment"]를 사용한다.
모든 활성 준비 검사는 공통 frame 생성에서 수행하므로 start·transition·call·restart에 적용된다. 실행 중에도 같은 입력/역할·현재 참조를 다시 확인한다. reason만으로 우회하지 않는다.
등록된 다른 작성 경로에서 실제 코드/행동을 바꿀 때도 관련 구현 라우트로 진행한다. flow API 밖의 파일 편집을 OS 수준으로 차단하는 기능은 아니다.

## 한 파일의 설계 계약

Markdown 정본의 첫 JSON fence와 관련 본문을 사용한다. [양식](../../../.agents/skills/plan-project/assets/reasons-canvas.md)을 필요한 범위에서 실제 내용으로 바꾼다. 기존 brief/설계에 이 계약을 둘 수 있으며 별도 상태 장부·일곱 문서 생성을 강제하지 않는다.

metadata의 필수 필드:

| 필드 | 계약 |
|---|---|
| version / kind | 정수1 / reasons-design |
| profile | behavioral, structural, editorial, exploratory 중 실제 변경 종류 |
| requirements | 중복 없는 R ID 목록 |
| operations | id, requirements, paths, depends_on, verification을 가진 O 목록 |
| decisions | id, status(resolved/open/proposed), operations, reason. 없으면 빈 목록 |
| references | 선택 항목. 재사용하는 로컬 정본의 path/sha256 목록 |
| not_applicable | 선택 항목. 작은 editorial/exploratory에서 영향 없는 관점과 구체적인 이유 |

본문은 `## Requirements`, `## Entities`, `## Approach`, `## Structure`, `## Operations`, `## Norms`, `## Safeguards`로 나눈다.
각 O는 Operations 안의 `### O1` 같은 실제 제목에 대응한다. 코드 fence 속 제목은 작업 경계가 아니다.
R/O 참조·중복·의존성 순환·필수 본문·현재 references 해시를 검사한다. Operations의 paths는 레포 상대 경로/pattern이며 변경할 task 범위를 덮어야 한다.

behavioral/structural은7관점의 본문을 갖는다. editorial/exploratory는 Requirements/Operations/Safeguards를 유지하며 나머지를 not_applicable의 사유로 짧게 처리할 수 있다.
본문/메타데이터가 형식상 있다는 것만으로 요구가 충분하거나 실제 사용자 합의가 있다는 뜻은 아니다. 프로필을 빌려 행동/권한/품질 경계 변경을 생략하지 않는다.
reference에는 재사용하는 의도/규칙/계약 정본을 둔다. 이번에 수정하는 구현 파일을 고정 입력으로 묶으면 그 편집 자체가 계약 변경으로 감지될 수 있다.

## 설계·정렬 근거를 task에 연결

명령은 레포 루트의 정상 Python으로 실행하고 실제 task/criterion/method/경로/증거 ID로 바꾼다. task의 방법·scope를 먼저 확정한다.

```sh
python3 tools/harness/run.py evidence add my-task --id DESIGN --type artifact --path docs/projects/my-project/design/my-feature.md --criterion A1 --method "실제 기준별 확인 방법" --description "현재 요구·R/O·경계를 기록한 설계"
python3 tools/harness/run.py flow alignment-template --task my-task --design DESIGN --operation O1 --basis REQUEST --output .runtime/my-task/alignment.json
```

생성물은 pending이며 자동 승인하지 않는다. 실제로 원문·의도·경계·범위·미결정을 검토한 뒤 작성한다.

| alignment 필드 | 확인할 것 |
|---|---|
| version / kind | 정수1 / reasons-alignment |
| design | 현재 design artifact의 path/sha256 |
| task_contract | 현재 task의 goal/scope/제약/입력/수용 기준·방법 계약 해시; 생성 시 현재 값 제공 |
| operations | 이번에 실행할 O. 선행 O가 먼저 오는 순서 |
| coverage | 모든 task 수용 기준 ID → 선택 O 목록. 빠진 기준/선택 O가 없어야 함 |
| basis | 실제 요청·기존 결정/원문의 기존 artifact/source 증거 ID. 설계/검토 자신으로 대체하지 않음 |
| evidence_bindings | basis/완료 의존성에서 참조한 각 evidence entry의 서명. 검토 당시의 연결을 보존하며 template --basis가 현재 값을 제공 |
| reviewer | name, type(agent/human), independent(실제 독립성) |
| decision / reason | 실제 판단 ready와 관측 이유. 아직 판단하지 못했으면 ready로 바꾸지 않음 |
| completed_dependencies | 선택하지 않았지만 완료를 확인한 선행 O → 기존 증거 ID |

basis나 완료 dependency의 원본·entry를 다른 유효한 파일로 바꿔도 검토 당시 서명과 다르면 거부한다. 실제 완료 dependency를 추가할 때도 그 entry 서명을 함께 묶는다.
선택 O에 영향을 주는 open/proposed 결정은 막는다. 다른 O에만 관련된 미결정은 독립된 현재 작업을 막지 않는다.
선행 작업은 선택 순서 앞에 있거나 완료 근거가 있어야 한다. 완료 근거의 의미는 실제 원문/검사와 대조한다.
task.scope는 선택 O의 paths 안에 있어야 한다. wildcard 범위는 명시적으로 같은 허용 pattern이 있어야 하며, 단순 fnmatch로 더 넓은 범위를 허용하지 않는다.

기존 사용자 요청/결정이 충분하면 그 근거를 basis에 연결하고 에이전트가 자체 검토를 기록한다. 같은 승인을 다시 묻지 않는다.
결과를 바꾸는 실제 선택이 필요할 때만 질문하고, 답변을 기다리는 의존 경로를 진행하지 않는다. 도구는 원문의 의미/사용자 신원을 인증하지 않는다.

```sh
python3 tools/harness/run.py evidence add my-task --id ALIGN --type artifact --path .runtime/my-task/alignment.json --criterion A1 --method "실제 기준별 확인 방법" --description "현재 설계·선택 O·결정 근거의 정렬 검토"
python3 tools/harness/run.py flow ready --task my-task --design DESIGN --alignment ALIGN
python3 tools/harness/run.py flow start my-flow --task my-task --node python-backend:implement --input design=DESIGN --input alignment=ALIGN
python3 tools/harness/run.py flow context my-flow --read
```

flow ready의 passed는 현재 파일/연결/범위/미결정·검토 형식의 준비 판정이다. 제품 요구 전체의 자동 승인으로 표시하지 않는다.

## 분석/설계/정렬 라우트

- plan-project:analysis는 요구·개념·대안·미결정을 분석한다.
- plan-project:design의 passed에는 실제 설계 Markdown artifact를 연결하며 result_checks=["design"]가 그 계약을 확인한다.
- plan-project:alignment에는 design 입력을 연결한다. actual review를 작성하고 passed에 alignment JSON artifact를 연결한다. result_checks=["alignment"]가 현재 design/task/선택 O에 맞는지 검사한다.
- 정렬 후 관련 구현으로 move할 때 `--input alignment=ALIGN`을 연결한다. 호출/전이의 대상이 같은 design/alignment 입력을 요구하면 현재 프레임의 유효한 동일 이름 근거를 상속한다. 명시 입력은 대상 계약으로 다시 검사한다.
- 구현 후 verify-work:check call도 같은 준비 근거를 전달받는다. 실패는 기존 재현/보완/회귀 경로로 처리한다.

## 변경과 재개

의도·관측 동작·권한·Safeguards가 바뀌면 관련 결정을 확인하고 docs-maintenance:intent-update에서 설계 정본을 먼저 갱신한다.
명세가 맞고 구현만 위반하면 요구를 바꾸지 않고 좁은 코드 수정/회귀로 진행한다. 동작을 유지한 정리는 implementation-sync에서 관련 구현 설명을 최신화한다.
관련 검토/검사·인덱스의 영향을 함께 확인한다. 전체 위키/Canvas 본문을 강제 로드하지 않는다.

현재 flow의 design/alignment는 최초 artifact 서명에 묶인다. 계약을 편집하면 옛 alignment를 다시 쓰지 못한다. 옛 근거는 당시 사본/이력으로 보존하고 새 DESIGN/ALIGN을 등록해 의도적으로 restart한다.
흐름 중 현재 입력인 설계를 직접 갱신하면 복귀할 호출자도 stale이 될 수 있다. 변경을 숨기지 말고 새 계약에서 설계/정렬을 재확인한다.
기존 flow는 바뀐 catalog를 감지해 명시적 restart를 요구한다. 완료된 task/review/당시 검사 증거는 소급 변경하지 않는다.

## 선택 읽기와 적용 한계

flow context는 현재 스킬 절차·공통 지침/프로젝트/보안/인덱스와 묶인 설계의 공통 계약·선택 O 본문을 제공한다.
무관한 O의 본문이나 전체 metadata를 미리 모델에 넣지 않는다. 명시적인 프로젝트 필수 문서가 있으면 유지한다.
내부 파서는 파일의 연결·한도·현재 SHA를 확인하기 위해 원문을 읽는다. 모델에 모든 원문을 전달한다는 뜻은 아니다.

이 기능은 선언/증거/범위 검사다. 의미적 설계 품질, 프로필 분류의 진실성, 선택의 권한, dependency 완료의 의미는 작성자/검토자가 실제 원문과 대조한다.
모델/셸·원격 도구·자동 설치·commit·사용자 승인 흐름을 추가하지 않는다. 자세한 배경과 채택/제외 이유는 [SPDD 조사](spdd-reasons-research.md), 상태 제어는 [스킬 흐름](skill-flows.md)을 따른다.
