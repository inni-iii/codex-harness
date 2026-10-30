# 설치 CLI 확인 기록

확인일: 2026-10-22 / 단계: 2 / 성격: 환경 조회와 옵션 확인

## 1. 확인 범위

`--version`, `--help`, `exec --help`, `login status`, `debug models`,
`debug models --bundled`, `features list`를 확인했다.
분류·작업용 모델 호출, 패키지 설치, 전역 Codex 설정 수정은 수행하지 않았다.
이 기록은 계정의 모델 실행 권한이나 결과 품질을 증명하지 않는다.

| 항목 | 관측값 |
| --- | --- |
| OS / 아키텍처 | macOS / arm64 |
| Python | 3.14.7 |
| Git | 2.55.0 |
| CLI | codex-cli 0.163.0 |
| 인증 상태 | ChatGPT 로그인 |
| 실제 실행 파일 진입점 | `/opt/homebrew/bin/codex` |

CLI에서 PATH alias 생성 권한 경고가 나왔으나, 버전·도움말·목록 조회는 정상 반환했다.
이를 수정하려고 시스템 권한이나 설치 경로를 변경하지 않았다.

## 2. CLI가 반환한 모델 목록

`codex debug models`는 `models` 배열을 반환했다.
출처는 `cli_resolved`로 기록한다. 이 출력만으로 서버 갱신 성공과
캐시 사용 여부를 구분할 수 없으므로 `live`라고 단정하지 않는다.
확인 당시 로컬 캐시 메타데이터는 client_version=0.163.0,
fetched_at=2026-10-22T05:51:49.560215Z였다. 이 값도 모델 실행 검증은 아니다.

| 목록의 공개 모델 | 지원 effort | 목록의 기본 effort |
| --- | --- | --- |
| gpt-6.1-sol | low, medium, high, xhigh, max, ultra | low |
| gpt-6-astra | low, medium, high, xhigh, max, ultra | medium |
| gpt-6-sol | low, medium, high, xhigh, max, ultra | medium |
| gpt-6-luna | low, medium, high, xhigh, max | medium |
| gpt-5.6-sol | low, medium, high, xhigh, max, ultra | low |
| gpt-5.6-terra | low, medium, high, xhigh, max, ultra | medium |
| gpt-5.6-luna | low, medium, high, xhigh, max | medium |

전체 9개 중 공개 모델은 7개, 숨김 모델은 2개였다.
공개 모델의 단일 에이전트 effort 조합은 35개, Ultra 조합은 5개다.
현재 `catalog`는 숨김 모델과 Ultra도 표시한다. 자동 추천은 공개된 초기 역할·effort 정책을 따른다.
35개 모두에 자동 추천 근거가 있다는 뜻은 아니다.
모두 text·image를 입력 형식으로 표기했지만, 이를 모든 도구의 지원으로 해석하지 않는다.

`--bundled` 목록은 11개로 위 반환 목록과 달랐다.
Astra의 기본 effort도 bundled에서는 low, 일반 반환 목록에서는 medium이었다.
따라서 내장 목록을 현재 계정의 가용 목록이나 검증된 fallback으로 사용하지 않는다.

정규화 대상 필드는 `slug`, `visibility`, `supported_reasoning_levels[].effort`,
`default_reasoning_level`, `input_modalities`다.
App Server의 `model/list` 형식과 raw CLI 형식을 섞지 않고 어댑터에서 변환한다.

## 3. 설치 버전에서 확인한 연결 지점

| 목적 | 확인한 옵션·명령 | 확인 수준 |
| --- | --- | --- |
| 작업 모델 지정 | `exec -m MODEL` | 도움말에서 확인 |
| effort 지정 | `-c 'model_reasoning_effort="medium"'` | 공식 설정 문서와 현재 설정 키 확인; 모델 호출 미수행 |
| 요청 전달 | `exec -` | 도움말의 stdin 입력 설명 확인 |
| 결과 형식 | `--output-schema FILE` | 도움말에서 확인; 실제 출력 미검증 |
| 기계 판독 이벤트 | `--json` | 도움말에서 확인; 실제 이벤트 내용 미검증 |
| 최종 결과 분리 | `--output-last-message FILE` | 도움말에서 확인 |
| 분류용 읽기 전용 실행 | `--sandbox read-only` | 도움말에서 확인 |
| 세션 비보존 | `--ephemeral` | 도움말에서 확인 |
| 사용자 설정 제외 | `--ignore-user-config` | 도움말상 인증은 CODEX_HOME을 사용 |
| 옵션 엄격 검사 | `--strict-config` | exec 도움말에서 확인; features에는 미지원 |
| 기존 세션 재개 | `exec resume SESSION_ID` | 도움말에서 확인; 첫 구현 범위 밖 |

`features list`에서 shell_tool, multi_agent, apps, plugins, hooks를
`-c features.<name>=false`로 지정하면 각 값이 false로 표시됨을 확인했다.
이는 feature 설정 반영 확인이며, 실제 분류 런타임의 전체 도구 격리 검증은 아니다.
`web_search="disabled"`도 분류 실행 시 명시할 예정이며 실제 호출은 아직 확인하지 않았다.

## 4. 초기 모델 설정

분류용 `gpt-6-luna / medium`을 고정했던 초안은 철회했다.
현재 설정은 비어 있으며 호출자가 정책 또는 명령 옵션으로 지정한다.
effort를 생략하면 해당 분류 모델이 목록에서 알리는 기본 effort를 사용하고 요청값을 결과에 표시한다.
분류 모델과 작업 모델은 서로 독립적이며, 실제 분류 품질과 비용 우위는 아직 평가하지 않았다.

작업용 기본 모델·effort는 지정하지 않는다.
사용자의 개인 기본 설정을 라우터의 작업용 fallback으로 복사하지 않는다.
작업마다 분류·정책·지원 조합을 적용하고, 적합한 후보를 결정할 수 없으면 상태와 이유를 반환한다.

## 5. 실제 분류·작업 실행 전 남은 확인

- 분류 프로세스에 실제로 노출되는 도구와 지침. 임시 경로·읽기 전용만으로 완전 격리를 주장하지 않는다.
- 사용자 설정 제외 이후에도 적용되는 전역 지침·관리 설정과 인증의 관계.
- CLI가 결과에 모델·effort·사용량을 어떤 근거로 제공하는지.
- 갱신 결과가 확인되지 않은 CLI 목록의 freshness와 캐시 정책.
- 숨김 모델, 새 effort, 알 수 없는 raw 필드에 대한 파싱·추천 정책.

다음 구현의 Python 최소 버전은 표준 TOML 파서를 사용할 수 있는 3.11로 정한다.
현재 확인한 3.14.7 이외의 Python 버전이나 OS에서의 동작은 아직 검증하지 않았다.

## 근거

- 로컬 CLI 0.163.0 도움말·버전·목록·로그인 상태와 feature 조회 결과.
- [공식 CLI 옵션](https://learn.chatgpt.com/docs/cli/reference)
- [공식 모델 목록 인터페이스](https://learn.chatgpt.com/docs/app-server#models)
- [공식 reasoning effort 설정](https://learn.chatgpt.com/docs/config-file/config-reference)
