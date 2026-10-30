# 작업 기록

2026-10-31. 사용자 승인 범위: 학습/기억·프로젝트 공유 → 스킬 작성 → 환경/패키지 관리자 → 설정 감사 보강.
공개 Codex 대안과 공식 문서를 대조한 선택은 [도입 기록](../../../tools/harness/docs/skill-sources.md)에 있다.

## 검증 계획

- 결과: 검토 지식의 조건별 재사용, 네이티브 스킬 관리, 저장소 계약 기반 설치, 원본 감사기 연결과 미확인의 명확한 구분.
- 범위: 신규 모듈의 정상/거부/경계 테스트, 실제 CLI 지식→스킬 흐름, 훅 stdin, 실제 오프라인 npm/uv, doctor/설정/전체 회귀. 실행 범위는 진행 중 사용자에게 알렸다.
- 앱 UI/API 변경이 없어 제품 브라우저 E2E는 비적용. 외부 브라우저·브라우저 설치·모델 호출을 실행하지 않는다.
- 첫 커밋이 없어 worktree 기준 HEAD를 만들지 않았다. 작업 전 소스를 로컬 별도 사본으로 보존했으며 다른 세션의 기존 구현/검사 변경을 유지한다. 최종 검사는 고정 source snapshot을 사용한다.

## 확인한 결함과 회귀

구현 중 확인/수정한 결함과 보존한 회귀:

- K1: 새 argparse 블록이 skill create 등록 중간에 삽입돼 --path 충돌. 블록을 분리했다. 실제 CLI 생명주기 테스트가 매 호출 파서 생성과 정상/중복 오류를 확인한다.
- K2: description 정규식의 줄바꿈 탐욕으로 생성 스킬의 본문 구분 실패. 한 줄로 제한하고 생성→검증→context 원문 테스트로 보존했다.
- K3: macOS /var와 /private/var 별칭 때문에 훅의 상대 경로 변환 실패. 루트를 resolve하고 실제 stdin 자식 프로세스 테스트로 보존했다.
- K4: 상위 workspace가 있는 하위 설치가 범위를 확장할 수 있음. 부모 선언을 검사해 설치 전 거부하며 Node/uv 회귀로 보존했다.
- K5: 저장된 지식의 state/history 누락·잘못된 형식을 초기 검사에서 통과시키면 후속 읽기가 실패할 수 있음. catalog 경계 검증과 malformed metadata 회귀로 보존했다.

현재 테스트: test_knowledge.py, test_skills.py, test_environment.py, test_agent_config.py.
별도의 수정 전 로그 파일은 보존하지 않았으며 위 재현 조건과 자동 회귀를 보존했다. 원본 mitam 구현의 탈락 사유는 도입 기록에서 별도로 다룬다.

## 인수인계

- 학습 기록은 docs/knowledge/catalog.json에, 실행/사용법은 tools/harness/docs의 knowledge·skill-authoring·environment·security 문서에 둔다. 개인 전역 파일을 요구하지 않는다.
- 검토 없는 자동 채택/전역 승격·배경 모델·외부 MCP 일괄 등록·GitHub CI는 제외했다. 범위 안의 로컬 소스/설정만 변경한다.
- 최종 명령: 레포 루트에서 .venv/bin/python tools/harness/run.py check --snapshot --full. 두 번째 사본의 doctor/agent-config/secret-patterns/python 전부 통과, unittest 302개·실패 0·skip 1. skip은 기존 test_execution의 샌드박스 그룹 신호 제한이다. 실행 시 live_source_changed=false였다.
- 현재 검증 보고서: .runtime/check-snapshots/4b2f8db48af1404cb25e469688efad2d/checks/c7d1c9c573e04637883615d74dbb6ec3/report.json. 첫 301개 결과는 검사 뒤 타 세션의 검토 규약/테스트 3파일 수정 때문에 당시 기록으로 보존하고 현재 증거에 재사용하지 않았다.
- 새 기능 집중 검사 33개는 모두 통과했다(.runtime/capabilities-targeted.log). 실제 CLI 지식→스킬 선택, 훅 stdin/입력 제한, npm lifecycle 비실행/lock 유지, uv 프로젝트 환경/lock 유지를 포함한다.
- 새 스킬 3개는 작성 도구의 quick_validate로 확인했고 주제별 context 원문과 무관한 조사에서 미선택도 확인했다. setup 읽기 전용 점검과 builtin config는 통과, 실제 AgentShield 명령은 unavailable/exit 2였다.
- CHECK_A1~A4와 SOURCES 증거를 task에 연결했다. 실제 엔진/네이티브 이벤트 후속 확인과 발견별 수정 전 근거의 보존 한계가 남아 있어 형식적인 완료 리뷰를 만들어 task를 닫지 않는다. 기록의 열림을 새 로컬 기능 실패로 해석하지 않는다.
- registry.npmjs.org가 ENOTFOUND라 AgentShield 배포본·integrity·실제 엔진 검증은 미확인. optional manifest와 CLI 어댑터만 준비했다. fake child fixture는 실엔진 검증을 뜻하지 않는다.
- Codex 네이티브 훅은 /hooks에서 정의 신뢰가 필요하다. 신뢰를 대신 설정하거나 실제 compact 이벤트가 실행됐다고 주장하지 않는다.
- 설치 네트워크가 가능한 환경에서 선택적 엔진의 lock 생성/검토→로컬 설치→정적 스캔을 확인하고, Codex에서 훅 정의를 검토한다. 명령은 security.md와 knowledge.md에 있다.

다른 노트북에 없는 로컬 로그는 재현 명령도 남긴다. 비밀값·개인 경로는 기록하지 않는다.
