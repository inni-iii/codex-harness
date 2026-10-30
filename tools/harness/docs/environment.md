# 환경 점검과 고정 의존성 설치

프로젝트 선언과 lockfile을 확인하고 명시적으로 요청한 로컬 의존성만 동기화한다.

```sh
python3 tools/harness/run.py setup
python3 tools/harness/run.py environment inspect --path frontend
python3 tools/harness/run.py environment install --path frontend
python3 tools/harness/run.py environment install --path backend --offline
```

예시 경로는 실제 manifest 위치로 바꾼다. inspect/setup 기본 동작은 읽기 전용이며 프로그램 존재를 접속·인증·설치 성공으로 표현하지 않는다.

| 대상 | 선택과 실행 |
|---|---|
| npm/pnpm | packageManager와 lockfile 일치. npm ci / pnpm install --frozen-lockfile |
| Bun | bun.lock 또는 bun.lockb. frozen-lockfile |
| Yarn | 정확한 major 필요. classic frozen-lockfile, modern immutable |
| uv | pyproject.toml+uv.lock. uv sync --locked, 프로젝트 .venv |
| Poetry | 감지하며 프로젝트 전용 설치 workflow 필요로 보고. 자동 설치하지 않음 |

여러 lockfile·관리자 충돌·버전 불일치·미설치 프로그램을 다른 관리자로 대체하지 않는다.
packageManager 버전은 실제 --version과 맞아야 한다. lockfile만으로 선택했으면 CLI 버전까지 고정됐다고 하지 않는다.
상위 pnpm/Node/uv workspace 선언을 발견하면 루트를 명시해야 한다. 멤버 glob을 추측해 하위 설치를 실행하지 않는다. 복잡한 workspace/plugin은 프로젝트 workflow에서 검토한다.
개인 전역 선호·CLAUDE_PACKAGE_MANAGER로 선택을 덮어쓰지 않고 관리자 자체를 자동 다운로드하지 않는다.
install은 lockfile을 갱신하지 않는다. 종료 후 manifest/lock 해시가 바뀌면 stale이다.
기본값은 lifecycle/build script 비활성화다. 필요한 native build·설치 스크립트는 검토 후 --allow-scripts로 허용하고 앱을 검증한다.
offline 경로는 npm/pnpm/uv이며 다른 관리자의 옵션을 추측해 실행하지 않는다.
캐시는 .cache, 로그는 .runtime/setup에 둔다. 설치 도구가 출력한 로그는 공유 전 검토한다.
여러 생태계 중 뒤의 설치가 실패해도 앞선 설치가 자동 rollback되지는 않는다. 임의 레포 실행을 격리하는 sandbox가 아니다.

공식 계약: [npm ci](https://docs.npmjs.com/cli/v11/commands/npm-ci/), [pnpm](https://pnpm.io/cli/install), [Yarn](https://yarnpkg.com/cli/install), [Bun](https://bun.sh/docs/pm/cli/install), [uv](https://docs.astral.sh/uv/concepts/projects/sync/).
