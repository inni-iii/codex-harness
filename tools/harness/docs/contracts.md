# 입출력 계약 초안

버전: 0.1 / 상태: `route` 구현 반영. 분류 JSON Schema는 코드에서 생성한다.
아래 요청 객체는 논리적인 계약이다. 현재 CLI는 요청을 옵션으로 받고, stdin에는 요청 문자열을 받는다.

## 1. 요청

```json
{
  "contract_version": "0.1",
  "prompt": "인수인계 자료를 바탕으로 결제 재시도 정책을 설계해줘",
  "cwd": "/path/to/project",
  "context_files": [".codex/handoffs/payment-research.md"],
  "preference": "quality",
  "override": null
}
```

| 필드 | 규칙 |
| --- | --- |
| contract_version | 첫 버전은 `0.1`이다. 미지원 버전을 거부한다. |
| prompt | 필수인 비어 있지 않은 요청이다. 작업 실행에 원문을 전달한다. |
| cwd | 존재하는 작업 디렉터리다. 내부에서는 절대경로로 정규화한다. |
| context_files | 기본값은 빈 배열. 상대경로는 cwd 기준이다. 지정 파일을 읽지 못하면 알린다. |
| preference | `economy`, `balanced`, `quality`. 기본값은 `quality`다. |
| override | null 또는 model·effort의 직접 지정값. 한 축만 지정할 수도 있다. 나머지는 작업 분류로 고른다. |

임의 셸 명령은 요청 계약에 포함하지 않는다. 실행기는 고정된 명령과 인자 배열을 구성한다.
알 수 없는 필드와 잘못된 자료형은 오류로 처리한다.
요청·맥락은 분류용 Codex로도 전달될 수 있으며, 분류 호출에 사용량이 발생한다.
분류기에 보낸 맥락과 작업기에 전달할 맥락을 식별할 수 있도록 원본 파일 정보를 관리한다.

## 2. 작업 분류

```json
{
  "source": "codex",
  "task_type": "design",
  "complexity": "high",
  "ambiguity": "medium",
  "failure_impact": "high",
  "verifiability": "partial",
  "context_dependency": "explicit_files",
  "missing_context": [],
  "uncertainties": ["외부 장애 시 재시도 요구사항이 확정되지 않음"],
  "required_capabilities": ["text"]
}
```

- source: `rules` 또는 `codex`.
- task_type: `answer`, `research`, `design`, `implement`, `debug`, `review`, `document`, `other`.
- complexity / ambiguity / failure_impact: `low`, `medium`, `high`, `unknown`.
- verifiability: `deterministic`, `partial`, `judgment`, `unknown`.
- context_dependency: `none`, `explicit_files`, `prior_session`, `unknown`.
- missing_context / uncertainties: 누락된 자료와 판단의 불확실성을 구분하는 문자열 배열.
- required_capabilities: 필요한 입력 형식·도구 등. 구현할 때 허용값과 판단 방법을 정한다.

분류 결과에는 모델명·effort·측정된 성공 확률을 넣지 않는다.
`unknown`을 규칙에서 임의로 `low`로 변환하지 않는다.

## 3. 라우팅 결정

```json
{
  "contract_version": "0.1",
  "decision_id": "<generated-id>",
  "status": "ready",
  "policy_version": "0.1.0-provisional",
  "catalog_source": "cli_resolved",
  "selected": {
    "model": "<actual-supported-model-id>",
    "effort": "<actual-supported-effort>"
  },
  "evidence_basis": "provisional_policy",
  "reason_codes": ["TASK_REQUIREMENTS_MATCHED", "PROVISIONAL_POLICY", "CLOSEST_SUFFICIENT_PAIR"],
  "policy_rule": "complex",
  "missing_context": [],
  "task_executed": false
}
```

위 꺾쇠 안의 값은 실행 가능한 설정이 아닌 설명용 자리표시자다.
`explanation`은 화면 표시용이며 원문 혼입을 피하기 위해 기본 로그에 저장하지 않는다.

| status | 의미 |
| --- | --- |
| ready | 지원 후보를 선택했다. 실행이나 정답을 뜻하지 않는다. |
| needs_context | 필요한 정보·지정 파일이 부족하다. |
| classification_required | rules-only 모드에서 규칙으로 결정할 수 없다. |
| config_required | 필요한 분류용 설정 또는 추천 정책이 지정되지 않았다. |
| unavailable | 유효한 목록 또는 적합한 실행 후보가 없다. |
| classifier_error | 분류가 실패했고 적용할 규칙 fallback이 없다. |
| invalid_input | 요청·경로·옵션이 잘못되었다. |

`ready` 이외에는 selected=null이며 작업용 Codex를 시작하지 않는다.
현재 evidence_basis는 `provisional_policy`, `user_override` 중 하나다. 실제 평가 연결 전 `evaluated`를 쓰지 않는다.
목록에 나온다는 사실과 측정된 능력·계정의 실행 권한을 동일하게 취급하지 않는다.
catalog_source는 확인된 서버 응답이면 `live`, 로컬 캐시면 `cache`,
CLI 내부의 출처 구분이 안 되면 `cli_resolved`, 사용자가 파일로 제공하면 `provided`로 기록한다.
내장 목록인 `bundled`는 실행 가용성의 근거로 사용하지 않는다.

## 4. 실행과 품질

`route`는 작업을 실행하지 않고 결과 JSON만 stdout에 출력하며 자체 결과를 영구 저장하지 않는다.
항상 task_executed=false이며 observed_model, observed_effort, usage는 null, quality는 unrated다.
작업 실행은 `run`/`chat`이 담당한다. 실행 필드·종료 코드·대기 요청·관측 범위는 [실행 계약](execution.md#결과와-실패-처리)을 따른다.
route의 기존 observed_model/observed_effort와 달리 실행 결과는 출처가 붙은 observed_configuration을 사용한다.
아래 원칙은 실행 및 후속 품질 평가에도 적용한다.

실행 기록은 decision_id로 연결하고 recommended와 observed를 나눈다.
모델과 effort를 관측하지 못하면 null, 확인 상태는 `unverified`다.
기본 설정이나 추천값을 observed에 복사해 실행 확인을 대체하지 않는다.

프로세스 종료 코드, Codex의 완료 상태, 품질 평가는 별개다.
품질은 `accepted`, `needs_revision`, `failed`, `unrated` 중 하나다.
사용자 수용, 기계적 검증, 리뷰 등 평가의 출처도 남긴다.
사용량·비용의 미측정 값은 null이다. 추정은 별도 필드에 근거와 함께 남긴다.
