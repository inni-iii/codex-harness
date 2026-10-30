# 실행 방법과 현재 추천 정책

이 문서는 필요할 때 직접 사용하는 추천 전용 `catalog`/`route`를 설명한다. 일반 작업에 라우팅을 강제하지 않는다.
별도 모델 실행을 명시적으로 선택한 경우 [실행 안내](execution.md)의 `run`/`chat`을 사용할 수 있다.

## 실행 환경

Python 3.11 이상과 설치·로그인된 Codex CLI를 사용한다.
현재는 별도 설치 없이 이 레포의 최상위 디렉터리에서 실행한다.
pip 설치나 전역 `harness` 명령 등록은 아직 제공하지 않는다.

```sh
python3 tools/harness/run.py --help
python3 tools/harness/run.py route --help
```

## 지원 목록과 모델 호출 없는 추천

```sh
python3 tools/harness/run.py catalog
python3 tools/harness/run.py route --rules-only "결제 버튼 문구만 '구매'를 '결제'로 바꿔줘"
python3 tools/harness/run.py route --rules-only "아까 정한 대로 구현해줘"
```

첫 추천 예시의 결과는 현재 CLI 목록 기준 `gpt-6-luna / low`였다.
마지막 요청은 이전 맥락이 없어 `needs_context`를 반환한다.
규칙만으로 분류하기 어려운 요청은 `classification_required`다.
두 상태 모두 작업을 실행하지 않는다. `route` 전체가 작업 실행 기능을 포함하지 않는다.
종료 코드는 ready이면 0, 추가 정보·설정·지원 확인 등이 필요하면 2다.

CLI의 모델 목록 조회는 수행하지만 분류 모델 생성 호출은 하지 않는다.
목록 JSON을 이미 갖고 있다면 `--catalog-file`로 제공해 완전히 오프라인으로 사용할 수 있다.
입력은 raw CLI의 models 배열 또는 모든 페이지를 모은 App Server data 배열이다.
목록 파일은 사용자가 제공한 자료라는 출처를 유지하며 실제 호출 권한을 보증하지 않는다.

## 직접 지정

```sh
python3 tools/harness/run.py route --model gpt-6-luna --effort max "독립된 작업의 추천 설정 확인"
```

두 값 모두 지정하면 지원 조합인지 검사해 그대로 반환한다. 분류 모델을 호출하지 않는다.
model 또는 effort 한 축만 지정할 수도 있다. 이때 작업을 분류한 뒤 나머지 축을 선택한다.
지원하지 않는 조합을 다른 값으로 바꾸지 않는다.
명시적으로 누락된 맥락 파일이나 이전 결정이 필요한 요청은 직접 지정해도 `needs_context`다.

## Codex 분류 호출

규칙으로 결정할 수 없고 `--rules-only`가 아니면 분류용 설정을 확인한다.
분류 모델은 임의로 정하지 않으므로, 미설정이면 `config_required`를 반환한다.
아래 MODEL_ID와 EFFORT를 사용하려는 분류 설정으로 바꾼다. 이 경로는 실제 모델 사용량이 발생한다.

```sh
python3 tools/harness/run.py route \
  --classifier-model MODEL_ID --classifier-effort EFFORT \
  --context-file tools/harness/docs/design.md "이 설계의 모호한 점을 검토해줘"
```

`--cwd`를 제공하면 상대 context-file 경로는 그 작업 디렉터리를 기준으로 읽는다.
분류 모델을 지정하고 effort를 생략하면 그 모델의 목록 기본 effort를 사용한다.
분류 호출의 대기 한도는 예시 정책의 30초이며 `--timeout`으로 변경한다.
타임아웃·잘못된 JSON·분류 중 도구 사용 이벤트를 오류로 처리하고 작업을 실행하지 않는다.
현재 명령 구성과 결과 검사는 대체 실행으로 검증했으며 실제 모델의 전체 도구·지침 격리는 미검증이다.

## 초기 추천 정책

모든 수치와 역할은 정책 구현을 위한 잠정 분류이며 측정된 성능·성공 확률이 아니다.
`tools/harness/policies/policy.example.toml`이 현재 실행에 사용되는 초기 정책이다.
다른 전체 정책 파일을 `--policy PATH`로 지정할 수 있다. 개인 Codex 설정의 작업 모델은 읽지 않는다.

| 작업 특성 | 초기 최소 역할 | 초기 최소 effort |
| --- | --- | --- |
| 복잡도·모호성·실패 영향이 모두 높음 | Astra 역할 | max |
| 복잡도·모호성이 높음 | Astra 역할 | xhigh |
| 복잡도 또는 실패 영향 또는 모호성이 높음 | Sol 역할 | high |
| 세 값 모두 낮고 요청 범위가 명확함 | Luna 역할 | low |
| 그 외 분류 완료된 일반 작업 | Terra 역할 | medium |

위 표는 특정 모델에 effort 상한을 씌우는 프로필이 아니다.
지원되는 모든 조합을 펼친 뒤 최소 요구에 맞는 후보를 비교한다.
기본 quality는 effort의 불필요한 상향, 역할의 불필요한 상향 순서로 줄인다.
economy는 역할 상향을 먼저 줄이고, balanced는 두 상향 정도를 함께 고려한다.
이는 품질·사용량의 실측 최적화가 아닌 초기 휴리스틱이다.
동률이면 위임 추가 여부, 정책의 모델 우선순위, 카탈로그 우선순위, 식별자 순서로 결정한다.

Luna/max도 후보이며 직접 지정할 수 있다. 정책 요구가 Luna 역할/max이면 자동 선택도 가능하다.
새 모델 또는 새 effort에 추천 의미가 정의되지 않았으면 목록에 보존하고 제외 이유를 출력한다.
새 모델을 직접 지정하는 경우 역할 점수 대신 사용자의 선택을 존중한다.
text·image 입력 형식은 목록으로 검사하지만, 웹·셸 등 도구 요구는 capabilities_to_verify로 남긴다.
ready는 추천 후보가 정해졌다는 뜻이며 실제 작업 환경의 모든 도구를 확인했다는 뜻이 아니다.

## 확인한 동작과 한계

자동 테스트는 JSON/정책 해석, 정보 부족, 한국어 문구 수정과 결제 로직 구분,
지원 조합 유지, 직접 지정, 고정 작업 모델 방지, 분류 오류·타임아웃을 다룬다.
실제 CLI로 목록 조회와 rules-only·직접 지정 경로도 확인했다.
이는 실제 모델의 분류 정확도나 작업 품질을 검증한 결과가 아니다.

```sh
python3 -m unittest discover -s tools/harness/tests -v
```

`route` 결과는 stdout에만 출력한다. 실제 작업 실행과 실행 기록은 `run`/`chat`이 담당한다.
사용자 평가 저장, 모델 비용 계산, 캐시 관리, 자동 학습, 전역 인수인계 자동 탐색은 아직 구현하지 않았다.
