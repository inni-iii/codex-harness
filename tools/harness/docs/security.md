# 로컬 보안 관리와 검사

설계·구현·검토의 시작점은 [security-review](../../../.agents/skills/security-review/SKILL.md)다.
이 문서는 실행 기능의 계약과 한계를 설명한다. GitHub 연결·CI/CD·AgentShield 런타임 차단 훅은 구성하지 않는다.
실제 재현으로 확인한 구현 보완과 신뢰 범위는 [2026-10-31 재점검](security-recheck-2026-10-31.md)에 남긴다.
명령은 레포 루트에서 정상 동작하는 Python 3.11 이상으로 실행한다.

## 프로젝트에서 사용하는 순서

1. project 명령으로 brief.md·security.md·draft workflow.toml을 만든다. 명령이 준비되면 active로 사용하면서 보안 설계를 병렬 보완할 수 있다. 프로필의 [security]에 문서 해시·자원·경계·항목별 판단·검사를 연결하고, [단계·범위별 판정](project-workflows.md#동시-작업의-미결-범위와-완료-판정)에 따라 미결을 관리한다.
2. context --kind plan --project ... --read로 프로젝트 자료와 설계 지침을 읽는다. 새 권한·외부 호출·의존성 경계를 발견하면 관련 주제를 추가한다.
3. 서버의 실제 처리 경계에 입력·권한·실행 검증을 구현한다. AGENTS나 프롬프트의 금지 문구로 대체하지 않는다.
4. 보호 조건에서 정상·거부·오류·경합 사례를 고르고 실제 API/파일/외부 호출 경계에서 실행한다. 제품 테스트는 프로젝트 checks에 등록하고 관련 UI 흐름은 E2E로 연결한다.
5. 기본 로컬 검사와 필요한 별도 의존성 조회를 수행한다. 발견은 재현→수정→같은 공격 사례와 정상 회귀로 확인한다.
6. 코드 상태·명령·결과·미실행·열린 발견을 보고한다. 앱 검사와 하네스 자체 검사를 구분한다.

```sh
python3 tools/harness/run.py context --kind implement --paths backend/items.py --topic security --read
python3 tools/harness/run.py context --kind review --paths tools/harness/harness/mcp.py --topic tool-responses --read
python3 tools/harness/run.py context --kind review --paths tools/harness/browser/package-lock.json --read
```

context는 원문 선택 보조다. 일반 backend/items.py처럼 이름에 auth가 없는 코드도 보안 스킬의 선별 절차를 읽게 한다.
상세 지침은 주제·경계에 따라 선택하며 매 작업에 모든 보안 검사를 강제하지 않는다.
현재 검사기는 앱의 자원 권한·SSRF·prompt injection 내성 등을 자동 판정하지 않는다.

## 오프라인 비밀값 패턴 검사

```sh
python3 tools/harness/run.py security secrets
python3 tools/harness/run.py security secrets --paths .env.example backend/settings.py
```

기본 입력은 Git의 현재 tracked+untracked 소스이며 ignore를 따른다. 미추적 파일도 포함한다.
과거 커밋·삭제 파일의 내용·ignored .env·.runtime·.venv·node_modules·개인 홈 전체를 검사하지 않는다.
Git 없는 소스 아카이브는 [core.py](../harness/core.py)의 소스 열거와 .env/local 설정 제외 규칙을 사용한다.
ignored 파일을 검사하려면 레포 안의 실제 파일을 --paths로 명시한다. 명시 디렉터리의 재귀 검사·외부 파일·심볼릭 링크는 지원하지 않는다.

규칙 버전 2는 private-key 표식·일부 GitHub/AWS/OpenAI/Anthropic/GitLab/Slack 토큰, Bearer 리터럴, DB 등 URL의 내장 자격 증명, 비밀값 의미의 변수/필드 할당을 검사한다.
할당은 접두사·camelCase·환경변수/JSON/YAML·따옴표 유무를 포함하고 파일 크기 한도 내 8자 이상 후보를 다룬다. 따옴표 안의 공백과 긴 값도 포함하며 같은 줄에 여러 규칙이 걸릴 수 있다.
명시적인 `${NAME}`·`$NAME`·`YOUR_API_KEY`·`REPLACE_WITH_API_KEY` 같은 참조/자리표시자는 값과 구분한다. test/example/synthetic이 들어 있다는 이유만으로 값 전체를 면제하지 않는다.
짧은 값·다른 제공자 토큰·분할/인코딩·문자열 조합·모든 문법을 완전히 탐지하지는 못한다. 고급 secret scanner의 대체나 비밀값 부재의 증명이 아니다.
실제 값처럼 보이는 합성 예제도 후보가 될 수 있다. 후보를 숨기는 임의 allowlist는 제공하지 않는다.
테스트는 유효하지 않은 값을 실행 중 조합해 사용한다. 실제 키를 검증하거나 외부로 보내지 않는다.

파일당 2 MiB·총 64 MiB가 한도다. 바이너리·잘못된 UTF-8·읽기 실패·크기 초과·위험 경로는 미검사로 남긴다.
후보는 최대 1,000건까지만 반환하고 그 뒤 범위는 finding_limit 미검사로 남긴다. 대량 입력으로 보고서를 무한히 키우지 않는다.
일부 미검사나 대상 0개는 통과가 아니다. 의도한 바이너리가 있다면 필요한 별도 검사와 범위를 정해 근거를 대조한다.
출력에는 파일·줄·규칙 ID·입력 전체 SHA-256을 남기고 매치·소스 행·환경 변수는 출력하지 않는다.
경로 자체는 남으므로 민감한 내용을 파일 이름에 넣지 않는다.

기본 check의 secret-patterns는 전체 소스를 오프라인 검사한다. 모델·네트워크·설치를 사용하지 않는다.
`covers_behavior = false`이므로 새로운 앱의 행동 검사 등록 부족을 가릴 수 없다.
예: frontend/New.svelte의 행동 검사가 없으면 패턴 검사와 무관하게 check는 needs_configuration이다.

## Codex 설정과 선택적 AgentShield

```sh
python3 tools/harness/run.py security config
python3 tools/harness/run.py security config --engine agentshield
```

기본 agent-config 검사는 Codex 설정의 위험 sandbox/approval 조합, 일부 MCP 실행/환경 전달, hooks JSON과 미지원 handler를 좁게 확인한다.
명령·훅의 실제 신뢰 상태·모든 프롬프트 공격·앱 보안을 판정하지 않는다. 현재 레포의 좁은 검사기가 AgentShield보다 우수하다는 비교 근거는 없다.

별도로 [생명주기 훅](hooks.md#원격-쓰기-보조-차단)의 PreToolUse는 직접 SSH 쓰기·업로드를 분류하고 PostToolUse는 변경된 설정의 정적 점검을 연결한다. 동적 구문·미관측 도구·콜백 실패를 포함한 완전한 차단 보장은 없으며, 원격 읽기 전용 규칙과 실제 실행 권한 경계를 대신하지 않는다.

AgentShield는 [공식 프로젝트](https://github.com/affaan-m/agentshield)의 CLI 정적 검사를 연결하는 별도 옵션이다.
[API 계약](https://github.com/affaan-m/agentshield/blob/main/API.md)에 따라 내부 scan 모듈 import 대신 scan --path ... --format json을 사용한다.
자동 수정·모델 호출·런타임 훅·online supply-chain 옵션은 전달하지 않는다. CLI 자식 환경에 개인 비밀값/설정을 전달하지 않는다.
AGENTS와 .codex 설정·네이티브 스킬/참조의 복사본을 임시 위치에서 검사하며 원본 위치로 역매핑한다.
중첩 .agents/skills는 원본 discovery의 누락을 피하도록 skills/rules 디렉터리의 평평한 복사본으로 제공한다.
파일 수·집계·종료 코드·위치를 대조하며 불일치/미설치는 incomplete/unavailable이다.
결과에는 위치·규칙 ID·심각도만 남기고 원문 evidence/description은 출력하지 않는다.
이 연결 계약 테스트는 실제 엔진의 탐지 정확도나 전체 탐지 범위를 입증하지 않는다.

2026-10-31 확인한 저장소 package.json의 버전 1.6.0을 선택 후보로 정확히 지정했다.
현재 셸의 registry.npmjs.org DNS가 ENOTFOUND로 실패해 패키지 배포본·전이 의존성·integrity를 검증하거나 설치하지 못했다.
따라서 tools/harness/security/package.json은 선택적 설치 명세이며 lockfile은 아직 없다. 기본 검사는 외부 엔진을 성공으로 간주하지 않는다.
네트워크가 가능한 로컬 환경에서 다음 순서로 잠금과 전이 의존성을 검토한 뒤 설치한다. 이 단계는 현재 실행 검증을 마치지 못했다.

```sh
npm install --package-lock-only --ignore-scripts --prefix tools/harness/security --cache .cache/npm
python3 tools/harness/run.py environment inspect --path tools/harness/security
python3 tools/harness/run.py environment install --path tools/harness/security
python3 tools/harness/run.py security config --engine agentshield
```

설치 전 Node 요구 버전·배포 출처·라이선스·advisory와 생성된 lock diff를 확인한다.
실제 보고서의 filesScanned 계약이 다르면 결과를 통과로 우회하지 말고 고정 버전의 discovery와 JSON을 재검증한다.

## 별도 네트워크 의존성 조회

```sh
python3 tools/harness/run.py security dependencies --npm-lock tools/harness/browser/package-lock.json --allow-network
python3 tools/harness/run.py security dependencies --requirements backend/requirements-audit.txt --allow-network
```

존재하는 실제 경로만 지정한다. 옵션은 반복 가능하며 지정한 대상을 모두 처리한다.
--allow-network가 없으면 외부 도구를 실행하지 않는다. 이 옵션은 해당 패키지 메타데이터 조회에만 적용하며 설치·수정·원격 쓰기 승인이 아니다.
패키지 이름/버전은 advisory 서비스로 전달된다. 사설 패키지 이름도 민감할 수 있으므로 전송 허용 여부를 먼저 판단한다.
기본 setup/doctor/check --full은 이 조회를 실행하지 않는다.

### npm 입력과 실행

이미 설치된 npm이 필요하다. 버전을 확인하며 설치·업데이트하지 않는다.
package-lock v2/v3, 같은 폴더 package.json, 정상 node_modules 경로·SHA-512 integrity·공개 registry.npmjs.org HTTPS 출처를 요구한다.
직접 의존성 그룹 불일치, workspace, file/link/VCS/alias 등 현재 미지원 입력은 설정 필요다.
manifest/lock만 비공개 임시 디렉터리에 복사해 `npm audit --json --package-lock-only --ignore-scripts`를 실행한다.
개인/프로젝트 .npmrc·node_modules·비밀값은 복사하지 않으며 user/global config·cache도 임시 위치를 사용한다.
상속 npm 설정을 제거하고 공개 registry·모든 심각도·dev/optional/peer 포함을 명시한다.
audit fix·install을 실행하지 않고 원본 manifest/lock을 바꾸지 않는다.
auditReportVersion=2의 JSON·종료 코드·집계·패키지 수를 대조한다. 형식 변경·누락·0개 조회는 오류다.

### Python 입력과 실행

이미 설치된 pip-audit가 필요하다. 전역 설치를 필수로 만들지 않는다. 도입 시 프로젝트 보안 도구 환경의 버전·설치 방법을 기록한다.
없으면 unavailable이며 통과가 아니다. 하네스의 표준 라이브러리 실행에는 필요하지 않다.
주석/빈 줄과 `패키지==정확한버전`만 있는 requirements를 받는다. **모든 전이 의존성을 포함한 목록인지 작성자가 실제 lock/환경과 대조해야 한다.**
범위 지정·환경 마커·include·URL·editable·옵션·hash 연속행을 부분 파싱하지 않는다. 미지원이면 needs_configuration이다.
격리 임시 디렉터리에서 `pip-audit --no-deps --disable-pip --format=json --vulnerability-service=pypi`로 조회한다.
resolver·설치·build backend를 실행하지 않고 토큰·pip 설정·PYTHONPATH를 상속하지 않는다.
결과의 모든 패키지/버전이 입력과 일치하고 skip이 없으며 exit code와 발견 수가 맞아야 통과한다.
uv.lock·pylock 등은 현재 지원하지 않는다. 필요하면 해당 형식과 도구 계약을 검증해 확장한다.

### 응답 처리와 보존

stdin을 닫고 stdout/stderr를 동시에 읽되 합계 2 MiB를 넘으면 중단한다. 실행 45초, 버전 조회 10초 한도다.
POSIX는 별도 프로세스 그룹을 종료해 자식과 출력 스트림을 정리한다. Windows는 현재 검증하지 않았다.
잘못된 UTF-8·JSON·중복 키·schema·종료 코드·0개 결과를 통과시키지 않는다.
stdout/stderr 원문·설명·URL·예외 문자열을 출력/영구 로그에 복사하지 않는다.
버전·입력 해시·종료 코드·안전한 패키지 식별/집계만 반환하고 응답을 명령으로 실행하지 않는다.
조회 중 원본 입력이 바뀌면 stale이다. 결과를 보존하려면 검토한 로컬 .runtime 하위로 리다이렉트한다.
임시 파일은 종료 시 삭제하지만 강제 OS/프로세스 종료 시 잔류할 수 있다. 입력 메타데이터에 실제 키를 넣지 않는다.

## 기존 MCP 연결 점검의 응답 경계

mcp-check는 설정에 명시된 HTTPS endpoint에 initialize·initialized·tools/list만 보낸다. 모델·도구 호출·서버 지시 실행은 하지 않는다.
리다이렉트를 자동 추적하지 않아 session header를 다른 목적지로 넘기지 않는다. URL의 userinfo·fragment도 거부한다.
현재 probe가 지원하는 protocol은 2025-03-26이며 다른 협상 결과는 지원 필요로 남긴다.
JSON-RPC 버전·요청 ID·result/error·중복 키·미디어 타입을 확인하고 notification은 빈 202 응답만 받는다.
session ID의 제어 문자·과대 길이·도중 변경을 거부하고, 응답 전체·SSE 누적 크기를 2,000,000바이트로 제한한다.
SSE를 크기 없는 readline로 읽지 않고 read1의 제한된 chunk로 처리한다. 서버 notification은 실행하지 않으며 서버의 추가 request는 지원하지 않는다.
tools/list는 첫 페이지의 이름·중복·항목 수를 확인하고 scope=first_tools_page와 more_tools를 표시한다. 전체 도구 동작 검사가 아니다.
오류에는 서버 본문·session ID·원본 예외·URL을 복사하지 않는다. 도구 설명이나 initialize.instructions도 실행/출력하지 않는다.
각 응답은 monotonic 경과 검사와 socket timeout을 함께 사용한다. 블로킹 read 중에는 deadline 감지가 늦을 수 있으므로 socket timeout만큼 초과할 수 있으며 정밀한 강제 실행 격리로 표현하지 않는다.
규격 근거는 [MCP HTTP transport](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports)와 [lifecycle](https://modelcontextprotocol.io/specification/2025-03-26/basic/lifecycle)다.

## 상태와 종료 코드

보안 CLI는 status=passed만 0, 나머지는 2다. 실제 스캐너 exit code는 별도 필드다.

| 상태 | 의미·다음 행동 |
|---|---|
| passed | 명시한 범위에서 패턴/advisory 후보 없음. 앱 보안 합격 판정 아님 |
| findings | 후보/advisory 있음. 실제 영향과 적용 버전 확인·수정/근거 기록 |
| incomplete | 일부 입력/도구/응답 미확인. 하위 결과 확인 후 보완 |
| no_inputs | 패턴 검사 대상 0개. 범위 확인 |
| needs_configuration | 대상 없음·미지원/위험 입력·lock 불일치 |
| network_not_authorized | 네트워크 opt-in 없음. 조회 미실행 |
| unavailable | 개별 스캐너 미설치 |
| error | 개별 실행·버전·한도·네트워크/응답 형식 오류 |
| stale | 조회 도중 원본 변경. 새 상태 재조회 |

발견과 오류가 섞이면 전체 incomplete이며 개별 findings도 남긴다.
알려진 advisory 조회는 도달 가능성·악성 패키지·출처 위조·미공개 취약점 검사와 다르다.

## 로그·재현과 현재 한계

일반 check는 기존 계약대로 원본 로그를 보존한다. 실행 디렉터리는 POSIX 0700, 로그 파일은 0600으로 생성한다.
원본 로그가 자동 마스킹된다고 주장하지 않는다. 앱·테스트에서 실제 키를 출력하지 않게 하고 trace·스크린샷도 공유 전 확인한다.
보안 전용 명령은 원본 매치와 스캐너 출력을 보존하지 않는다. 두 보존 계약을 구분한다.

지침·양식·코드는 모두 레포에 있다. 전역 skill-creator는 작성 때 참고했으며 실행·설치·검증 의존성이 아니다.
[스킬 관리](skill-authoring.md)와 doctor·자체 테스트로 다른 노트북에서도 검사한다.
Codex 실행 프로그램·정상 Python·관련 외부 도구는 환경마다 준비한다. 레포 복사로 OS 권한·네트워크·로그인까지 복제되지는 않는다.
자체 테스트는 합성 키·임시 Git·가짜 스캐너 응답·실제 자식 프로세스를 사용한다.
이는 실제 advisory 조회와 별도 근거이며 아직 없는 서비스의 인증·파일·API·모델 내성을 시험한 결과가 아니다.
