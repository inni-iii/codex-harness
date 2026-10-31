# 로컬 E2E 실행을 프로젝트에 연결

## 준비

실제 앱 URL·서버 시작·테스트 데이터·인증·정리 범위를 확인한다. 원격 SSH 서버에서 설치·서버·테스트를 실행하지 않는다.
도구/앱이 없거나 띄울 수 없으면 그 범위를 미실행으로 남긴다. 브라우저 MCP 연결과 자동 검사 runner의 실제 실행은 구분한다.
기존 package.json·packageManager·잠금 파일·Playwright config·테스트·서버 시작 명령부터 확인한다.
@playwright/test는 해당 프로젝트에 로컬 설치하고 버전을 잠금 파일로 추적한다.
기존 runner가 없다면 현재 지원 버전과 Node 요구를 공식 문서에서 확인해 선택한다.
브라우저 MCP 패키지 설치가 테스트 runner 설치를 대신하지 않는다.
추가 전역 설정·개인 브라우저 프로필을 필수 의존성으로 만들지 않는다.

npm 프로젝트 예: 설치 버전을 결정한 뒤 npm install --save-dev --save-exact @playwright/test@버전,
이후 npm ci와 프로젝트 로컬 playwright install chromium을 사용한다.
다른 패키지 관리자는 해당 프로젝트의 공식 명령을 따른다. 테스트 중 npx 자동 다운로드를 기대하지 않는다.

## 템플릿 사용

assets/playwright.config.cjs를 실제 앱 package.json이 있는 위치로 복사한다.
example.spec.ts는 실제 tests/e2e 위치에 옮겨 경로·입력 label·응답·정리 fixture를 바꾼다.
설정의 E2E_BASE_URL과 E2E_START_COMMAND는 프로젝트의 실제 로컬 URL·시작 명령으로 정의한다.
Python API도 시작해야 하면 E2E_API_URL/E2E_API_START_COMMAND를 함께 정의한다.
필요한 값을 프로젝트별 config에 직접 명시해도 된다. 비밀값은 공유 config에 넣지 않는다.

webServer로 로컬 서버를 시작하고 종료하게 하며, reuseExistingServer는 기본으로 끈다.
기존 서버를 사용할 때는 테스트 환경임을 확인한 뒤 명시적으로 선택한다.
템플릿의 globalTimeout은 하네스 check timeout보다 짧게 유지해 runner가 서버를 정리할 시간을 둔다.
서버 readiness는 검사가 필요한 의존성이 준비됐는지 확인하는 URL을 사용한다.
이 템플릿은 특정 Svelte 실행 방식·FastAPI·DB를 전제하지 않는다.

## 하네스 검사 예

다음은 실제 frontend config/테스트/서버가 준비된 프로젝트에서 조정하는 예다.

```toml
[[checks]]
id = "ui-e2e"
command = ["node", "tools/harness/scripts/run-playwright.mjs", "--project-dir", "frontend", "--report", "{report}", "--", "--grep", "@smoke"]
cwd = "."
paths = ["frontend/**", "backend/api/**", "shared/**"]
test_summary = "junit"
cacheable = false
run_at = ["feature", "integration", "final"]
timeout = 180

[[checks]]
id = "ui-e2e-full"
command = ["node", "tools/harness/scripts/run-playwright.mjs", "--project-dir", "frontend", "--report", "{report}"]
cwd = "."
paths = ["frontend/**", "backend/**", "shared/**"]
tier = "full"
run_at = ["feature", "integration", "final"]
test_summary = "junit"
cacheable = false
timeout = 300

[[impacts]]
paths = ["backend/auth/**", "shared/**"]
checks = ["ui-e2e", "ui-e2e-full"]
reason = "Shared auth/contract change affects existing user journeys."
```

E2E 선택 경로는 실제 구조에 맞춘다. --grep은 해당 태그를 가진 실제 테스트가 있을 때만 사용한다.
빠른 편집 검사는 --checkpoint edit로 실행하고 의미 있는 사용자 기능 묶음 완성 시 feature로 실행한다.
작업 시작에 이번 검증 범위·E2E 여부/시점을 알린다. --full은 checkpoint와 관계없이 전체 등록 검사를 선택한다.
실행기는 프로젝트 로컬 runner를 찾고 HARNESS_JUNIT_REPORT/HARNESS_E2E_ARTIFACTS로 새 경로를 전달한다.
프로젝트 config가 이 환경변수를 사용해야 한다. 보고서가 없으면 하네스는 실패시킨다.
Playwright JUnit 출력에는 --outputFile 옵션을 복사하지 않는다. 해당 옵션은 다른 runner와 혼동하기 쉽다.
설정된 JUnit reporter를 CLI --reporter로 덮어쓰지 않는다.

E2E 시작 명령·데이터 전제·필수 흐름을 프로젝트 개요와 프로필에 연결한다.
필요한 E2E가 등록되지 않았으면 설정을 보완하고 미확인으로 남긴다.

공식 근거: [webServer](https://playwright.dev/docs/test-webserver), [reporter](https://playwright.dev/docs/test-reporters).
