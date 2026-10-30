# 전체 연결·문서 재점검 기록

2026-10-31. 추가 기능의 전체 레포 연결과 문서 구조·중복·설명 일치 점검.

## 범위와 기준

AGENTS·context·스킬·참조·hooks/config·CLI·소비 모듈·등록 검사·현재 안내·과거 이력을 대조한다. 193개 소스 중 Markdown 108개에서 로컬 링크377개를 검사했다. 초기 파일/앵커 후보0·180자 이상 완전 동일 문단0. 앵커는 GFM 유사 정적 판정이며 렌더 검증은 아니다.
변경 전 소스는 .runtime/capabilities-audit-baseline/source, 구조 결과는 .runtime/capabilities-doc-audit.json에 보존했다. 다른 세션의 UserPromptSubmit/라우팅·문서 관리·검토 규약은 보존한다. Git HEAD가 없어 새 worktree 기준 커밋을 만들지 않는다.
브라우저 UI 변경이 없어 제품 E2E는 비적용이다. 로컬 CLI/단위·통합 검사와 문서 참조를 확인한다.

## 발견과 재현

- F1 학습 훅: SessionStart가 채택 지식의 lesson을400자/conditions를200자로 잘라 전달하고 exclusions를 누락한다. 조건부 교훈의 의미가 바뀔 수 있다. 기대: 적용·제외 조건을 함께 완전한 단위로 전달하거나 ID와 원문 조회로 연결한다.
- F2 문서 불일치: workflows.md의 CLI 자동 수행 부재 설명이 현재 run/chat과 다르다. maintain-knowledge의 모든 Codex 훅에 대한 무모델 설명은 UserPromptSubmit 라우팅과 충돌한다. knowledge의 자연어 적용/제외 조건과 kind/topic/path OR 선택을 구분해야 한다. 구조 지도에 새 파일 위치가 일부 빠져 있다. 서로 다른 문서의 목적을 유지하면서 정본으로 연결한다.
- F3 잘못된 지식 형식: state=[] 입력이 ValueError 대신 TypeError를 발생시킨다. CLI/doctor가 유효하지 않은 지식의 원인을 JSON 오류로 반환하지 못할 수 있다. history.action의 배열도 같은 경계다. 기대: catalog 검증 단계에서 일관되게 거부.
- F4 저장 용량: 후보1200개·topics 각100개인 약1.03MB bundle import가 passed로 끝나지만 실제 저장물은2.38MB여서 곧바로 catalog 재읽기가 실패한다. compact JSON으로 크기를 검사하고 들여쓰기 JSON으로 저장한 차이다. 기대: 실제 직렬화 크기를 검사하고 기존 catalog를 보존한다. export도 import 가능한 크기를 넘기지 않아야 한다.

## 실행 환경과 독립 검증

필수 run을 실행했으나 classifier_error/CLASSIFIER_FAILED, task_executed=false였다. 실제 분류 명령의 진단은 failed to initialize in-process app-server client: Operation not permitted. 지원되는 CLI 인자는 확인했으며 권한을 우회하거나 같은 요청의 모델을 바꿔 재시도하지 않았다. 수행 가능한 비모델 점검·검사 경로의 결과와 실모델 작업 검증을 구분한다.
과거 Claude/Codex 전체 가용 루트를 검색했고 기존에 읽은 원문을 재사용했다. 최근 Codex 10/31 기록에서도 같은 초기화/신뢰 한계가 확인된다. .claude/plans는 없다. 접근 가능한 모든 원문을 전부 읽었다고 주장하지 않는다.

## 보완과 최종 검증

F1/F3/F4 수정 전: .runtime/capabilities-audit-red/ee36bb657f984503b7a4d972157218a3/report.json. 실제 등록 python 검사307개에서 실패3·오류4를 관측했다. 같은 test_knowledge.py 해시의 회귀를 수정 없이 유지했다.
수정 후 지식 집중19개 전부 통과: .runtime/capabilities-audit-targeted-green.log. 큰 export 합성 입력은 원본catalog 1,868,928바이트/기존bundle 2,101,033바이트로 반례를 확인했고, 보완 후 ValueError·출력 미생성·원본 유지가 확인됐다.
최종 명령은 레포 루트의 .venv/bin/python tools/harness/run.py check --snapshot --full. 보고서는 .runtime/check-snapshots/2293aa137f534d12a5b85368e420411b/checks/8928bed8901e42d48deaf103129cea0e/report.json. doctor/agent-config/secret-patterns/python 통과, 307개·실패0·기존 환경skip1, live_source_changed=false. 새로운 실행/기록 오류는 없다.
최종 정적 문서 검사는109개/로컬링크393개·깨진 파일0·앵커 후보0·180자 이상 완전 동일 문단0. 결과는 .runtime/capabilities-doc-audit-final.json. 의미 중복은 관련 스킬·매뉴얼·워크플로·지식 문서를 원문으로 대조해 정리했다. task notes는 디렉터리/CLI에서 발견하며 초기 references의 읽기 경로를 현재 구조 안내에 연결했다.
새 기능의 기술 계약·명령·선택 원문과 현재 채택 지식의 증거는 일치한다. 현재 스킬14개와 공통 지식1개를 확인했다. 환경 스킬/AgentShield 어댑터는 코드 변경 없이 기존 검사를 재사용하고 전체 회귀로 통합 확인했다.
작업 결과는 [result.md](result.md)에, 발견별 회귀/문서 전후 대조/검토 라운드는 review.json에 연결했다. 최종 판단은 자체 검토이며 독립 에이전트 품질 평가가 아니다.
