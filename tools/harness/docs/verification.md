# 검증 실행과 근거

캐시·원본 요약·동시 편집·실험 원본의 추가 판정은 [검증 무결성](verification-integrity.md)을 따른다.

모든 명령은 레포 루트에서 실행한다. Python 3.11 이상이며 기본 점검·검증은 모델과 네트워크를 호출하지 않는다.

```sh
python3 tools/harness/run.py doctor
python3 tools/harness/run.py check --plan
python3 tools/harness/run.py check
python3 tools/harness/run.py check --paths AGENTS.md
python3 tools/harness/run.py check --full
python3 tools/harness/run.py check --reuse
python3 tools/harness/run.py check --staged
python3 tools/harness/run.py check --snapshot --paths tools/harness/harness/checks.py
```

Make 사용 환경에서는 make doctor/check/test/check-full/check-staged가 같은 진입점을 제공한다.
make check-plan은 검사 선택, make check-quick은 edit, make check-feature는 feature checkpoint, make check-reuse는 명시적인 결과 재사용이다.
Windows 등 Make가 없는 환경은 Python 명령을 사용한다. 다른 OS에서의 실행은 아직 실측하지 않았다.

## 선택과 결과

- 기본은 staged·unstaged·미추적 변경을 합쳐 선택한다. --paths는 명시한 범위에 한정하며 전체 검증으로 보고하지 않는다.
- --full은 등록된 모든 검사다. 저장소에 없는 앱 검사까지 실행되는 것이 아니다.
- doctor는 문법·링크·스킬·공유 설정을 확인한다. 제품 동작을 증명하지 않는다.
- 코드·의존성·설정이 바뀌면 관련 검사를 선택한다. 영향 분석이 불확실하거나 공유 영역이면 범위를 넓힌다.
- 대응 검사가 없는 새 앱 파일은 needs_configuration으로 종료한다. 기존 하네스 테스트로 대체하지 않는다.
- 통과·실패·검사 없음·설정 필요·실행 중 소스 변경(stale)을 구분한다.
- 보안 검토 미결은 테스트 실행을 막지 않는다. 해당 범위 검사만 통과하면 checks_passed_security_pending이며 completion_ready=false다. edit/feature의 개발 실행은 종료 코드 0, integration/final 및 --full은 2다. 실제 검사 실패는 계속 실패다. 범위별 미결·공유 영향은 [프로젝트 명세](project-workflows.md)를 따른다.
- unittest/JUnit 결과는 실행 수와 건너뜀을 검사한다. 0개·전체 건너뜀/expected failure·누락/잘못된 보고서는 통과가 아니다. 실패 요약이 있으면 종료 코드 0이어도 실패다.
- 경로는 레포 안의 실제 상대 경로로 정규화한 뒤 검사·보안 영향 규칙과 대조한다. ./·중복 슬래시·내부 ../ 표기 차이로 필수 검사를 피할 수 없다. 레포 밖 경로는 거부한다.
- 실제 파일의 대소문자·Unicode 별칭도 정규화한다. 설정 패턴은 정확한 소스 이름을 쓰며 ./·중복 슬래시·끝 슬래시·역슬래시는 오류다.
- unittest는 모든 실행 요약과 OK/FAILED/NO TESTS RAN을 대조하고 실패·오류·unexpected success를 확인한다. 성공 요약 누락·서로 모순되는 판정·중복/음수/실행 수를 넘는 집계는 잘못된 보고서다. 여러 runner 결과는 마지막 것만 취하지 않고 합산한다.
- FAILED에서 여러 subTest가 실패하면 실패 이벤트 수가 테스트 메서드 수보다 클 수 있다. 이를 실제 실패로 기록하며 실행 오류나 통과로 바꾸지 않는다. OK의 모순된 집계는 계속 거부한다.
- 원본 로그와 report.json은 .runtime/checks 아래 보존하고 stdout에는 구조화한 요약을 반환한다.
- 실행 디렉터리는 POSIX 0700, 원본 로그는 0600으로 생성한다. 일반 로그는 자동 마스킹되지 않으므로 합성 데이터를 사용한다. 보안 전용 검사의 최소 정보 출력은 [별도 계약](security.md)을 따른다.
  원본에는 도구가 출력한 데이터가 있을 수 있으므로 공개 자료로 복사하기 전에 확인한다.

## 검사 등록

### 의미 있는 작업 경계

check의 기본 checkpoint는 feature다. 사용자 기능은 작성→저장→재조회처럼 결과를 얻는 흐름이며 버튼·파일별로 나누지 않는다.
작업 시작에 [검증 경계](../../../.agents/skills/verify-work/references/checkpoints.md)에 따라 이번 검증 범위와 E2E 수행 여부·시점을 알린다.
구현 중에는 --checkpoint edit, 기능 묶음 완성 시 feature, 독립 변경을 합칠 때 integration, 제출 판단 시 final을 사용한다.
checkpoint는 자동 단계 진행이나 의미상 완료 판단이 아니다. final만 지정한다고 전체 suite가 선택되지는 않는다. 전체 등록 검사는 --full이다.

비싼 검사에는 다음 필드를 등록할 수 있다.

```toml
run_at = ["feature", "integration", "final"]
```

run_at을 생략하면 모든 checkpoint에 적용한다. tier/paths/always 등 기존 선택 조건도 함께 적용한다.
현재 시점에 미룬 검사는 deferred_checks에 표시한다. 빠른 검사만 성공하면 checkpoint_passed, 선택 검사 없이 전부 미뤘으면 deferred다.
이 상태는 사용자 기능 전체 검증 완료가 아니다. 미룬 검사를 인수인계하고 해당 경계에서 수행한다.
미등록 경로는 계속 needs_configuration이다. --full과 명시적인 공유 impacts는 시점 조건보다 우선한다.
영향이 큰 인증·공유 계약 변경 때문에 E2E를 앞당기면 실행 전에 이유와 범위를 알린다.

독립 작업을 합친 결과의 검사는 [세션·통합 도구](sessions.md)를 사용한다.

### 명령과 결과

tools/harness/harness.toml의 checks 배열에 명령, 작업 경로, 영향 경로, timeout을 등록한다.
지원하지 않는 검사 필드는 설정 오류다. 순서·병렬·재시도 기능을 임의의 키로 추가해 실행됐다고 가정하지 않는다.
명령은 shell 문자열이 아닌 인자 배열이다. {python}은 현재 인터프리터, {report}는 실행별 새 JUnit 파일 경로로 바뀐다.
test_summary=unittest 또는 junit을 지원한다. pytest/Vitest 등은 실제 runner의 JUnit 출력 옵션을 연결한다.

`covers_behavior = false`는 비밀값 패턴 검사처럼 앱 동작 검증을 대신할 수 없는 검사에 사용한다.
명령 선택·실행은 동일하지만 신규 소스의 행동 검사 등록 부족을 숨기지 않는다. 생략 시 true이며 doctor는 항상 행동 커버리지에서 제외한다.
기본 secret-patterns는 전체 현재 소스의 제한된 패턴 검사다. 네트워크 의존성 조회는 check --full에 포함하지 않는다.
JUnit 파서는 Python 표준 XML 모듈을 사용한다. doctor가 XML 모듈을 사용할 수 없다고 안내하면 Python 환경을 먼저 확인한다.
종료 코드만 사용하는 lint/build 검사는 테스트 실행 수를 증명하지 않는다.
실제 프론트·백엔드가 생기면 타입/정적 검사·관련 테스트·OpenAPI 생성물·핵심 브라우저 흐름을 등록한다.
외부 호출·DB·브라우저 검사는 환경 상태에 의존하므로 cacheable을 false로 둔다.

사용자 흐름의 Playwright 검사는 [E2E 스킬](../../../.agents/skills/e2e-testing/SKILL.md)을 따른다.
폼·탐색·인증·프론트/API 연결·공통 UI 동작 변경에는 관련 E2E가 필요하다. 관련 시나리오/smoke부터 실행하고 공유 영향에 맞춰 넓힌다.
[설정·등록 예시](../../../.agents/skills/e2e-testing/references/setup.md)의 프로젝트 로컬 runner와 새 JUnit 출력을 연결한다.
MCP는 브라우저 조작 도구이며 자동 테스트 runner를 대신하지 않는다. 앱이 없는 현재는 E2E 절차·템플릿·실행 연결을 제공하며 실제 제품 E2E를 통과로 표시하지 않는다.

프로젝트별 검사·항상 실행하는 스모크·공유 영향 impacts·전체 검사 tier는 [프로젝트 프로필](project-workflows.md)에 정의한다.
check --plan과 report.json의 selection_reasons에서 어떤 경로·공유 규칙 때문에 선택됐는지 확인한다.
경로 규칙은 실제 의미상 의존성을 자동 추론하지 않는다. 에이전트가 발견한 새 경계를 설정과 검사에 반영한다.
요구에서 도출하는 범위는 [검사 설계](../../../.agents/skills/verify-work/references/impact.md), 결과 판정은 [근거](../../../.agents/skills/verify-work/references/evidence.md)를 따른다.

## 재사용 조건

재사용은 --reuse를 명시하고 cacheable=true인 검사에만 적용한다.
소스·테스트·설정·로컬 환경 파일·환경변수·Python/플랫폼·등록 명령·범위에 해당하는 상태가 같아야 한다.
파일 지문은 보수적으로 전체 소스를 포함한다. .runtime·캐시·설치 디렉터리는 제외한다.
명시적으로 Git 추적한 소스는 관례적인 build/dist 등의 이름만으로 제외하지 않는다. 런타임 출력 자체를 추적하면 오류다.
docs/projects/build처럼 문서 영역의 프로젝트 이름도 지문에서 빠지지 않는다. 지문에서 제외된 기존 파일을 --paths로 지정하면 설정 필요로 남긴다.
따라서 설치 디렉터리 수동 수정이나 외부 서비스 상태를 추적하는 완전한 빌드 캐시는 아니다.
그런 상태에 의존하는 검사는 재사용하지 않는다. 로그가 사라졌거나 실행 중 소스가 바뀌면 재사용하지 않는다.
환경변수의 값은 지문 계산에만 사용하고 보고서에 저장하지 않는다.
파일 내용과 함께 실행 권한 비트도 비교한다. 내용이 같아도 실행 가능 여부가 달라지면 이전 통과를 재사용하지 않는다.
완료 근거의 환경에는 Python 버전뿐 아니라 실행 파일·실행 환경 prefix도 포함한다. 설치된 모든 패키지의 무결성까지 추적하지는 않는다.
작업 디렉터리·셸 수준과 무관한 도구 호출 추적 ID는 환경 지문에서 제외한다.

## 동시 편집 중 고정 사본 검사

```sh
python3 tools/harness/run.py check --snapshot --paths backend/items.py backend/tests/test_items.py --checkpoint feature
python3 tools/harness/run.py check --snapshot --full --checkpoint integration
```

--snapshot은 Git staging/커밋 없이 현재 공유 소스를 .runtime/check-snapshots/<실행ID>/source에 복사하고 그 사본의 실행기로 검사한다.
캡처 전후 원본 지문이 달라지면 capture_changed로 종료하고 명령을 실행하지 않는다. 사본 검사가 시작된 뒤 원본 편집은 계속할 수 있다.
보고서에는 snapshot_directory·snapshot_origin·live_source_changed와 소스별 해시를 남긴다. 여러 실행은 별도 디렉터리와 로그를 쓰며 전역 검사 잠금을 걸지 않는다.
재사용 캐시는 원자적으로 교체한다. 동시 작성으로 캐시 항목을 잃으면 새 검사를 수행하며 불완전한 JSON을 통과 근거로 쓰지 않는다.
손상된 캐시 구조도 재사용하지 않는다. 기본 .runtime 경로를 symlink로 다른 위치에 연결해 쓰는 방식은 지원하지 않는다.

이 사본에는 무시된 .env·개인 설정·.venv·node_modules를 복사하거나 연결하지 않는다. 소스 symlink도 거부한다.
현재 인터프리터와 상속 환경변수는 사용하므로 OS 보안 sandbox나 비밀값 차단기가 아니다. 외부 상태·포트·DB/브라우저 데이터는 별도 격리한다.
의존성 설치를 자동 수행하지 않는다. 프로젝트가 사본 안에서 필요한 환경을 재현하지 못하면 미확인/실패로 남긴다.
--staged·--reuse·--plan·사용자 report 디렉터리와 함께 쓸 수 없다. 검사 계획은 별도로 확인한다.
사본의 .runtime/source-inputs.json은 원본의 명시적 공유 소스 목록이다. index 사본에도 같은 목록을 남겨 Git metadata 부재로 추적 입력이 누락되지 않게 한다.
이 목록은 기본 입력을 줄이지 않는다. .env 등 원래 무시된 개인 파일·설치 트리를 추가로 가져오는 기능이 아니다.
사본 실행기 자체도 시간·4 MiB 출력 제한을 적용한다. 결과 보고서는 실행별 개인 폴더에 있어야 하며 원본 요약·소스·환경과 종료 상태를 대조한다.

사본의 통과는 그 사본에 한정된다. 원본에 적용한 현재 완료 근거로 연결하려면 출처 작업 폴더·현재 전체 소스·환경과 일치해야 한다.
무관해 보이는 파일도 현재의 보수적인 전체 소스 비교에서는 stale을 일으킬 수 있다. 이를 우회해 지문에서 빼지 말고 worktree로 작업을 분리한다.
긴 검사 전에 사본을 고정하는 비용이 있으므로 일반 편집에는 관련 검사와 유효한 --reuse를 사용하고, 실제 동시 편집이 있는 검사에 사본을 선택한다.
편집 역할·공유 계약·통합 순서는 [협업 지침](../../../.agents/skills/plan-project/references/collaboration.md)을 따른다.

## 커밋 대상 검증

--staged는 Git index를 임시 폴더로 export하고 그 안의 실행기·소스·테스트를 실행한다.
원본 index·작업 트리·환경 파일을 수정하거나 원본 node_modules/.venv를 연결하지 않는다.
미추적 파일 덕분에 불완전한 커밋이 통과하는 문제를 검사할 수 있다.
검증 전후 index가 바뀌면 stale이다. 아직 staging하지 않은 작업을 자동으로 git add하지 않는다.
현재 stdlib 검사에는 별도 설치가 필요 없다. 앱 의존성이 생기면 임시 사본 안에서 잠금 파일 설치도 연결해야
CI와 동등한 환경이라고 말할 수 있다. 그 전에는 검사 실패/환경 미확인으로 남긴다.

검증 결과는 요구사항별 실제 동작·연구 근거·실험 조건과 함께 판단한다.
하네스는 체크 결과만으로 task를 complete로 바꾸거나 product_accepted=true를 만들지 않는다.
별도 [완료 절차](completion.md)에서 실제 증거와 기준별 리뷰를 연결한 뒤 명시적으로 complete한다.

## 실행 제한·불안정 결과·원본 무결성

일반 check와 로컬 실험은 공통 processes.execute 실행기를 쓴다. 셸 없이 argv로 실행하고 stdin을 닫으며
stdout/stderr를 한 스트림으로 배출한다. 메모리에 전체 출력을 쌓지 않고 max_output_bytes까지 파일에 보존한다.
기본은 4 MiB, 설정 가능한 범위는 1 byte~64 MiB다. 신뢰한 종료 사유 표시가 이 상한 뒤에 소량 추가될 수 있다.
상한을 넘기면 output_limit이며 원래 종료 코드가 0이어도 통과하지 않는다. 로그를 잘랐는데 완전한 테스트 결과처럼 보고하지 않는다.

POSIX에서는 새 세션/프로세스 그룹으로 실행하고 종료 시 그룹의 TERM/KILL을 수행한다.
부모가 먼저 끝나도 자식이 출력 파이프를 잡고 있으면 제한 시간까지 대기한 뒤 종료를 시도한다.
권한 때문에 그룹 종료가 거부되면 루트 프로세스를 종료하고 process_group_cleanup_denied로 실패한다.
이 경우 자손 전체 종료를 보장하지 않으며 환경을 해결하기 전 같은 작업을 무제한 재실행하지 않는다.
스스로 새 세션으로 빠져나간 프로세스·OS sandbox·모든 Windows 트리 종료까지 보장하는 보안 격리기가 아니다.
Windows는 taskkill 기반 최선의 처리를 제공하지만 실제 지원 검증은 별도다.
[Python subprocess](https://docs.python.org/3.12/library/subprocess.html)의 timeout/Popen/session 계약을 참고했다.

JUnit은 실제 testcase와 suite 오류를 세며 파일은 16 MiB 이하의 새 일반 파일이어야 한다.
XML의 DTD/엔티티 선언은 지원하지 않는다. 최대 깊이는 64, 최대 노드는 250,000이며 초과하면 잘못된 보고서다.
읽기 자체의 크기와 파싱 중 구조를 제한하고 suite 집계는 노드를 반복해서 재탐색하지 않는다.
선언한 tests·errors·failures·skipped는 음수가 아닌 정수여야 한다. 선언한 tests/skipped와 실제 testcase/skip 수의 불일치는 잘못된 보고서다.
집계만으로 실제 testcase 실패를 상쇄하지 않는다. 지원하지 않는 runner 형식은 조용히 통과시키지 말고 어댑터를 확인한다.
flakyFailure/flakyError/rerunFailure/rerunError가 있으면 flaky_count에 기록하고 기본적으로 flaky라 판정한다.
[Surefire 재시도 XML](https://maven.apache.org/surefire/maven-surefire-plugin/examples/rerun-failing-tests.html)의 확장 태그도 놓치지 않기 위한 처리다.
check에 allow_flaky=true를 명시한 예외만 통과시킬 수 있고 해당 수는 보고서에 계속 남는다.
이는 모든 runner의 재시도 형식을 자동 인식한다는 뜻이 아니다. Playwright 기본 예제는 retries=0을 유지한다.

재사용에는 기존 소스/환경 지문뿐 아니라 로그·JUnit 파일의 SHA-256 일치도 필요하다.
원본 삭제·변조·구버전 무해시 캐시는 새 실행으로 대체한다. 보고서에는 파일별 소스 해시와 환경의 해시도 남겨
완료 시점에 실제 대상 상태를 대조한다. 환경변수 값·소스 본문은 내보내지 않는다.
Makefile 변경도 Python 동작 검사를 선택하며, 회귀 검사는 임시 Git 레포에서 실제 make 단계 전달과 실패 전파를 실행한다.

작업의 task.json/review.json은 doctor가 점검하는 기록 메타데이터다. 리뷰 생성 후 후속 검사에서 미등록 코드로 차단하지 않는다.
같은 작업 폴더의 helper.py와 임의 JSON은 이 예외에 포함하지 않는다.
작업별 적정 범위·맥락 선택과 오케스트레이션 판단은 [전체 연결 점검](verification-audit.md)을 따른다.
