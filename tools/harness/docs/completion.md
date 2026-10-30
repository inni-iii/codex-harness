# 작업 완료와 증거 연결

새 review v2에는 [검토 라운드와 결함별 회귀](review-rounds.md)가 필요하다. 한 요청 안에서 발견 사항을 처리하고 최종 상태를 재검토한 뒤 닫는다.

캐시/보고서 요약의 모순과 완료 도중 작업·리뷰 변경을 확인하는 상세 기준은 [검증 무결성](verification-integrity.md)을 따른다.

작업 생성은 수행을 시작하는 기록이며 완료 증명이 아니다. `check`도 task를 자동 완료하지 않는다.
완료 기록을 남기는 작업은 다음 순서로 진행한다. 작은 대화 답변마다 task 파일을 강제하지 않는다.

1. `task`로 목표와 관측 가능한 수용 기준을 만든다. 생성 형식은 version 2다.
2. 실제 입력·범위·제약을 채우고 기준별 확인 방법을 정한다. 검증 범위와 E2E 시점을 먼저 알린다.
3. 작업 결과와 필요한 검사를 만든다. 체크 실행 전 결과 문서도 확정한다.
4. `evidence add`로 실제 파일을 연결한다. 검사라면 보고서 안의 실제 동작 check ID도 지정한다.
5. `review-template`을 만들고 기준마다 증거가 요구를 증명하는 이유와 한계를 작성한다.
6. `evidence verify`로 연결을 확인하고 `evidence complete`로 기록을 닫는다. 확인 실패는 `needs_revision`이다.

## 종류별 최소 근거와 의미상 판단

| 작업 | 실행기가 요구하는 최소 유형 | 리뷰에서 판단할 내용 |
| --- | --- | --- |
| research | source + artifact | 질문에 답하는 결론, 원문의 버전·날짜·조건, 반증과 대안, 미확인 범위 |
| experiment | experiment + artifact | 비교 가능한 기준선/후보, 품질 하한·전체 실패, 가설을 지지하는 범위 |
| design | artifact | 사용자 결과·기존 계약, 품질 시나리오, 대안/위험/트레이드오프, 구현·검사 가능성 |
| implement | check | 정상 결과·해당 오류·공유 계약·주변 회귀, 해당하면 의미 있는 기능 E2E |
| debug | check | 수정 전 재현 근거, 원인과 좁은 수정, 수정 후 재현 제거·관련 회귀 |
| review | artifact | 검토 대상 상태, 요구 충족과 결함 구분, 구체적 위치·재현·영향·남은 한계 |

최소 유형을 채웠다는 이유만으로 내용이 옳아지지 않는다. 각 수용 기준에 실제로 관련된 근거가 있어야 한다.
예를 들어 API 응답 테스트는 브라우저에서 새로고침 후 저장 결과가 보인다는 조건 전체를 증명하지 않는다.
그 조건에는 실제 앱 E2E와 해당 시점의 환경을 연결한다. 아직 실행하지 못했으면 완료를 보류한다.

설계 종류 `design`의 기본 맥락은 계획·품질 요구다. 순수 UI 설계는 우선 `--topic ui-design`을 쓴다.
실제 화면 구현·렌더링·상태 검증까지 다루면 `ui`와 Svelte/토큰 경로를 추가한다.
경로와 주제는 OR 조건이므로 구현 경로를 추가하면 관련 E2E/검증 절차도 선택될 수 있다.
아키텍처 검토에 색상·서체 결정을 자동으로 강제하지 않는다.

## 타입별 저장 내용

모든 근거는 새 ID, 레포 상대 파일 경로, SHA-256, 설명, 기록 시각을 가진다.
`task.json`의 `evidence` 객체가 원본이고 수용 기준의 evidence 배열은 그 ID를 참조한다.
파일 누락·경로 탈출·별칭·symlink·내용 변경을 거부한다. task.json/notes.md/review.json은 그 작업의 결과 근거로 쓸 수 없다.

- `artifact`: 결론·설계·재현 분석·검토 결과 같은 실제 산출물. 존재와 해시를 확인한다.
- `source`: 실제로 읽은 원문의 로컬 메모/발췌 기록 + `--origin` 원본 HTTP(S) URL + 접근 시각.
  과거에 읽은 자료를 연결하면 `--accessed-at 2026-10-31`처럼 실제 접근일을 지정한다. 생략하면 현재 시각이다.
  웹 전체 복사 대신 주장·조건·버전·날짜·직접 링크와 필요한 최소 발췌를 남긴다. 도구가 URL의 사실성을 대신 판정하지 않는다.
- `check`: 현재 실행기의 report.json + `--check` 실제 동작 검사 ID. 전체 보고서가 passed이고 미룬 검사가 없어야 한다.
  doctor·secret-patterns만으로 구현 완료를 증명할 수 없다. edit checkpoint도 완료 증거로 쓰지 않는다.
  보고서의 모든 로그·JUnit 해시와 대상 소스/환경을 확인한다. lint/build는 동작 테스트와 구분해서 리뷰한다.
  이름만으로 판정하지 않고 검사 결과의 covers_behavior=true를 확인한다. false 또는 해당 metadata가 없는 옛 보고서는 현재 구현 완료 근거로 거부한다.
  applicable_pending이 있거나 checks_passed_security_pending인 보고서는 완료 근거로 거부한다. 개발 검사 종료 코드 0만으로 완료하지 않는다.
  독립 범위의 passed에 project_pending이 남아 있으면 리뷰에서 작업 범위와 미결 항목의 관계를 확인한다. 프로젝트 전체 보안 완료로 확대하지 않는다.
- `experiment`: [실험 실행기](experiments.md)의 통과한 run report. 원본 metrics·로그와 집계·반복·단위·품질 하한을 대조한다.
  비교 결과만 있거나 일부 실패를 뺀 최고 결과로 완료하지 않는다. 해석 artifact에 기준선/후보 비교 보고서도 연결한다.

구조화 JSON은 중복 키·NaN/Infinity·지수 표기의 무한대 변환·64단계를 넘는 컨테이너 중첩·16 MiB 초과를 거부한다. 원본 실험 metrics는 1 MiB까지다.
기록 갱신은 같은 디렉터리의 임시 파일 후 원자적 교체를 사용한다. 이것이 여러 작성자의 동시 편집 잠금은 아니다.
하나의 task 기록은 한 세션이 작성하고, 독립 작업은 기존 worktree 절차로 분리한다.

## 구현 작업 예

아래 이름·명령은 설명용이다. 실제 프로젝트에 등록된 check와 실제 보고서 경로를 사용한다.
명령은 레포 루트에서 실행하며 `python3`은 프로젝트에서 정한 정상 인터프리터로 바꿀 수 있다.

```sh
python3 tools/harness/run.py task persist-item --kind implement --goal "항목 저장과 재조회" --acceptance "저장 후 다시 조회해 같은 값을 얻는다"
python3 tools/harness/run.py check --paths backend/items.py backend/tests/test_items.py --checkpoint feature
python3 tools/harness/run.py evidence add persist-item --id E1 --type check --path .runtime/checks/실제실행ID/report.json --check items-integration --criterion A1 --method "저장 후 별도 조회 요청으로 확인" --description "실제 저장소를 이용한 생성/재조회 통합 검사"
python3 tools/harness/run.py evidence review-template persist-item
```

생성한 `docs/tasks/persist-item/review.json`을 읽고 채운다. reviewer는 실제 검토 주체,
reviewer_type은 agent/human, independent는 실제 독립성이다. 동일 작성자의 자체 검토는 false다.
criteria의 각 decision을 passed/그 외 상태로 판단하고 reason에 관측 결과와 요구의 연결을 적는다.
limitations에는 검증의 제한을, blockers에는 해결이 필요한 차단 사항을 적는다. blocker가 하나라도 있으면 닫히지 않는다.
빈 이름·이유, pending 판정, 빠진 기준, 근거 ID 불일치, 바뀐 계약/근거에 대한 옛 리뷰는 거부한다.

```sh
python3 tools/harness/run.py evidence verify persist-item --review docs/tasks/persist-item/review.json
python3 tools/harness/run.py evidence complete persist-item --review docs/tasks/persist-item/review.json
```

추가 사용자 승인을 매번 요구하는 절차가 아니다. 권한 범위 안에서 에이전트도 검토를 작성하고 완료할 수 있다.
현재 시스템은 사람/에이전트의 신원이나 독립성을 인증하지 않는다. 이를 보안 인증이나 블라인드 평가로 표현하지 않는다.

## 현재 결과와 과거 기록을 구분하기

완료 직전에는 보고서의 파일별 소스 해시와 현재 상태, 실행 환경 지문을 대조한다.
파일 실행 권한과 Python 실행 파일·환경 prefix도 확인한다. 해당 metadata가 없는 옛 보고서는 현재 실행기로 다시 검사한다.
작업 기록을 갱신하는 것만으로 항상 stale이 되는 순환을 피하려고 **그 작업의** task.json·notes.md·review.json만 비교에서 제외한다.
그 폴더의 helper.py나 실제 코드·입력·결과 문서는 제외하지 않는다. 계약은 목표·범위·제약·입력·선행 작업과 기준/방법의 별도 해시로 묶는다.
계약이나 증거를 바꾸면 새 리뷰가 필요하다. 다른 작업의 수정으로 보수적으로 stale이 되면 격리 공간과 실제 영향 범위를 다시 확인한다.
check --snapshot 보고서도 출처 작업 폴더와 .runtime/check-snapshots 아래 사본 경로를 확인하고 현재 전체 소스·환경과 대조한다.
다른 세션의 수정 전 사본이 통과했어도 현재 상태와 다르면 당시 기록으로만 남긴다. 작업 폴더 간 결과를 경로만 바꿔 차용하지 않는다.

완료 후의 기록은 당시 결과다. 나중에 소스가 바뀌어도 doctor가 모든 옛 작업을 실패 처리하지는 않는다.
당시 파일·로그·리뷰의 무결성은 계속 확인하고, `evidence verify`로 **현재도 유효하다**고 주장할 때는 현재 소스와 다시 대조한다.
원본 로그가 다른 노트북에 없으면 현재 결과를 검증했다고 말하지 말고 재현 명령으로 다시 실행한다.
doctor는 공유 기록이 참조하는 .runtime 원본이 없는 경우 과거 로컬 근거를 현재 확인할 수 없다는 note를 남기고
기록의 구조만 점검한다. 설정 설치를 막지는 않지만 해당 작업의 증거가 검증됐다고 표시하지도 않는다.
완료·현재 재사용·평가 명령은 누락된 실제 증거를 계속 거부한다. 공유 산출물 누락·구조 오류·존재하는 원본의 변조는 별도로 확인한다.
환경 지문은 설치된 모든 패키지·DB·외부 서비스 상태를 추적하지 않는다. 이런 조건은 별도 기록하고 해당 검사를 재사용하지 않는다.

version 1의 옛 planned/in_progress 작업은 구조를 계속 읽는다. 옛 complete의 문자열 evidence는 검증된 완료로 인정하지 않는다.
이관할 때 version 2, typed evidence 객체와 review를 만들고 기존 기준을 보존한 채 실제 근거를 다시 연결한다.
자동으로 경로 문자열을 사실 확인된 증거로 승격하거나 누락된 기준을 삭제하지 않는다.

근거의 존재와 재현 가능한 핵심 기능 확인을 구분하는 기준은 [JOSS 검토 기준](https://joss.readthedocs.io/en/latest/review_criteria.html)을 참고했다.
논문 공개·GitHub 운영·장기간 개발 같은 JOSS 제출 요건을 이 로컬 하네스의 의무로 가져오지는 않았다.
