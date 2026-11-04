# 작업 기록

중요한 발견·실패·정정과 그 근거를 날짜와 함께 기록한다.
공통 규칙으로 만들 후보는 적용 조건·제외 조건·재현/회귀 근거를 함께 남긴다.

## 검증 계획

- 사용자 결과 기준의 의미 있는 작업 묶음: 공식/원저 방법론 비교와 기존 research의 분석 절차/선택 연결, 실제 합성 사례.
- 이번 검증 범위·checkpoint와 사용자에게 알린 내용: 선택/비선택/호출/복귀와 빈 입력 경계, 합성 CSV/JSON, 통합 final 등록 검사.
- E2E 수행 여부·시점·사유와 미룬 검사: 앱/UI 변경이 없어 브라우저 E2E 비적용. 이번 수용 기준을 미룬 검사는 없다.
- 격리 위치·기준 상태·통합 시 함께 유지할 요구: 기존 .worktrees/docs-index를 재사용해 현재 main 소스에서 시작하고, baseline SHA 대조 뒤 범위17파일만 통합했다. 다른 세션의 프로젝트 문서/검증/훅 변경을 보존했다.

## 확인한 결함과 회귀

실제 결함을 확인하면 ID·증상·재현 입력·기대 결과·근거를 즉시 적는다. 추측과 환경 오류는 구분한다.
수정 전 실패·수정 후 통과·테스트/시나리오 위치·검사 수집 조건·미실행 이유를 보존한다.
마지막 수정 뒤의 재검토를 남기고 review.json의 verification.findings/rounds에 연결한다.

## 인수인계

- 목표·범위·현재 상태와 이어서 읽을 자료:
- 확정 결정·이유·미결정:
- 수용 기준별 실제 명령·cwd·대상 상태·결과·근거 위치:
- 실패/탈락한 방법·당시 조건·재검토 조건:
- 남은 문제·환경 전제:
- 다음 한 행동(파일/함수/명령과 관측할 결과):

다른 노트북에 없는 로컬 로그는 재현 명령도 남긴다. 비밀값·개인 경로는 기록하지 않는다.

## 2026-11-04 조사 시작

- 기존 research에는 기술 조사/근거/검색이 있고 experiment는 가설·비교·예산을 담당한다. CSV/JSON의 질문→품질→분석→결론 계약은 아직 없다. 사용자 원문과 양쪽 전체 접근 가능 기록을 재검색했고 새 관련 결정은 현재 대화에 있다. Claude plans 없음/archived JSONL0.
- 최초 context의 evidence 주제는 미등록이라 실패했다. technical-choice/skill-maintenance/web-search로 바로잡아 선택 원문을 읽었다. 실제 제품 결함으로 세지 않는다.
- 공식/원저: NIST, PPDAC 교육부 원문, CRISP-DM 원본, 정부 품질/2025 AQuA, Wickham 원논문 초록, ASA 공식 성명, pandas/scikit-learn/SciPy 공식 문서. IBM 웹/PDF403, PMC 브라우저 확인 화면 및 Europe PMC 도구 접근 불가는 원문 확인 성공으로 세지 않았다. CRISP 원본은 공개 대학 보관본의 저자·판·본문을 확인했다.
- 검증: 선택/비선택·flow 정상/근거부재, 합성CSV/중첩JSON의 품질과 분모/집계 반례를 실제 계산한다. 앱/UI 변경이 없어 브라우저 E2E 비적용. 새 패키지는 설치하지 않는다.

## 격리 보완과 사례

- research 설명/작업 표와 전용 참조·가벼운 양식, context4주제, analyze-data 라우트와6개 이동을 보완했다. 초안 뒤 현재 범위/원문을 정렬하고 maintain-skills 실행 흐름에 연결한 상태에서 실제 선택/분석/검증을 수행했다.
- 신규 선택/비선택·호출/복귀·근거부재4개는 모두 통과했다. 일반 config/package/task JSON과 다른 연구에는 데이터 참조를 강제로 넣지 않았다. research 최소 형식과 doctor도 통과했다.
- 실제 합성 분석: raw24→중복1제거23→채널누락1제외22. A6/11 vs B7/11이나 easy5/6 vs7/10, hard1/5 vs0/1. 금액오류1건은 전환에는 유지했다. 알려진 금액22건 소계1300은 전체매출로 주장하지 않았다. 중첩 주문3개/금액200이 항목 전개 후 잘못 합산하면260이 됨을 확인했다. 원본2파일 SHA 유지.
- 새 패키지/모델/실서비스 호출 없이 표준 csv/json/Decimal/Fraction을 사용했다. 라이브러리/모든통계 판단 정확성이나 인과를 자동 검증한 것으로 확대하지 않는다.

## 최종 통합·완료 검토

- 격리 check --full: 482개 중 실패0·기존 skip1. 현재 main에서 check --full --snapshot --checkpoint final: 496개 중 실패0·기존 skip1. 다른 세션의 이미 통합된 검사14개도 현재 사본에 포함됐다. 신규4개는 모두 실행/통과했다.
- 최종 보고서: .runtime/check-snapshots/ce9f71888dd84489af1f64f899e261c0/checks/4b06135ab6a14bddb0a179dfa6a56e9c/report.json. cwd는 레포 루트, source는 보고서의 고정 사본, 종료0. live_source_changed=true의 유일한 차이는 실행 중 생성한 이 작업 review.json이었다. 실제 source 비교와 완료 검사에서 이 bookkeeping 예외를 명시한다.
- 기존 skip 이유: sandbox가 프로세스 그룹 신호를 제한해 descendant cleanup 검사의 parent_exit=False 하위 사례를 실행할 수 없음. 이번 분석 연결 검사는 skip되지 않았다.
- skill validate research·최종 doctor·git diff --check 통과. 흐름은 유지보수→검증 호출/복귀→문서 동기화/검증→지도에서 finished. 통합 시 경로 기반 카탈로그가 달라져 동일 계약/설계/정렬로 명시 restart했다. 실제 구현 오류로 세지 않는다.
- 완료 기준/출처11개/결과/입력/실제 계산·재현 코드/등록 검사를 typed evidence로 연결하고 자체 review를 작성했다. findings=[]이며 합성 반례를 기존 하네스 결함으로 꾸미지 않는다.
- 해석/검증 한계는 report/sources/scenarios와 review에 유지했다. 실제 사용자 데이터나 독립 모델 성능·전체 통계 기법의 정확성을 측정한 결과가 아니다. 코드/입력/출력 근거는 .runtime/research-data-analysis에서 재현한다.
