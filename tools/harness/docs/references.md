# 참고 자료

확인일: 2026-10-22. 원본 프로그램의 실행·품질 비교를 재현한 것은 아니다.
외부 코드나 파일을 이 레포에 복사하지 않았다.

## 공식 문서

- [Codex 비대화형 실행](https://learn.chatgpt.com/docs/non-interactive-mode):
  분류와 작업 실행을 위한 `codex exec`, 구조화된 출력의 연결 지점.
- [Codex App Server 모델 목록](https://learn.chatgpt.com/docs/app-server#models):
  모델별 지원 effort와 기본값을 조회한다. 실제 연결 방식은 설치 CLI 확인 후 정한다.
- [Codex 모델 안내](https://learn.chatgpt.com/docs/models):
  모델·effort 선택과 Ultra의 하위 에이전트 실행 특성.
- [모델 선택 가이드](https://learn.chatgpt.com/docs/model-selection):
  추천을 출발점으로 사용하고 같은 입력에서 모델과 설정을 비교하는 원칙.
- [하네스 안에서의 평가 사례](https://developers.openai.com/cookbook/examples/partners/harness_aware_plugin_evals/harness_aware_plugin_evals):
  분류·단독 호출의 평가와 실제 Codex 하네스의 성능을 구분해야 하는 근거.

## 공개 구현과 참고할 아이디어

| 자료 | 참고할 부분 | 적용 한계 |
| --- | --- | --- |
| [Saadfk/codex-model-router](https://github.com/Saadfk/codex-model-router) | 분류용 Codex 격리, 스키마 검사, 규칙 fallback | 고정 계열·정책을 그대로 채택하지 않는다. |
| [Codex Smart Router](https://github.com/giovannimirarchi420/codex-smart-router) | 맥락 기반 분류, 직접 지정, 실행 기록 | 추정 비용 비교와 실측된 품질 비교를 구분한다. |
| [RouteLLM](https://github.com/lm-sys/RouteLLM) | 요청 분포에 맞춘 기준 보정과 고정 설정 비교 | 두 모델 중심의 평가를 다중 모델·effort에 그대로 일반화하지 않는다. |
| [auto-model-router](https://github.com/fstandhartinger/auto-model-router) | 분류·선택·예측·관측의 분리 | 전체 프록시·모델 제공자 구성을 이 프로젝트에 가져오지 않는다. |
| [Codex Session Handoff](https://github.com/lifang336/codex-session-handoff) | 프로젝트별 인수인계 자료 | 초기에는 명시적으로 지정한 자료 전달부터 구현한다. |

## 사용자 결정 반영

- 2026-10-19: 규칙과 분류 모델을 함께 사용하고, 분류 모델은 Codex CLI로 호출한다.
- 2026-10-19: 범용 공통 하네스 기능을 하나의 레포 안에서 모듈로 관리한다.
- 2026-10-20: 지원 모델·effort 조합을 좁은 고정 프로필로 제한하지 않는다.
- 2026-10-21: 첫 시도 품질과 재작업 감소를 우선하되, 모든 요청에 최고 설정을 쓰지 않는다.
- 2026-10-22: 단계별로 진행하며, 현재는 로컬 프로젝트와 설계 문서부터 만든다.
