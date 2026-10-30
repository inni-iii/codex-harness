# 세션 격리와 합친 결과 검증

레포 루트에서 실행한다. 로컬 Git만 사용하며 설치·모델 호출·자동 staging/commit/push·배포는 수행하지 않는다.
Git worktree를 만드는 명령은 로컬 Git 메타데이터와 새 작업 폴더를 만든다. 원격 SSH 서버에서 실행하지 않는다.

## 작업 시작

```sh
python3 tools/harness/run.py session status
python3 tools/harness/run.py session start save-and-find --goal "작성·저장·재조회로 결과 확인" --scope 'frontend/**' --scope 'backend/**'
```

start는 깨끗한 커밋 기준에서 harness/<이름> 브랜치와 .worktrees/<이름>을 만든다.
새 코딩 세션을 그 작업 폴더에서 열어 수행한다. 이미 연결된 worktree에서는 status로 확인하고 기존 격리를 재사용한다.
기준 커밋이 없거나 시작 체크아웃이 수정 중이면 중단하고 이유를 반환한다. 현재 변경을 몰래 제외하거나 자동 커밋하지 않는다.
현재 이 하네스 레포에는 아직 첫 커밋이 없어 실제 작업용 start는 기준 커밋 마련 후 사용할 수 있다.
Git 테스트는 별도 임시 레포에서 검증하며 이 레포의 사용자 변경·index·브랜치를 커밋하지 않는다.

scope는 의도를 기록하는 값이지 강제 파일 잠금이 아니다. 다른 세션의 자동 생성·메시지 교환·감시도 하지 않는다.
작업마다 포트·DB/데이터·브라우저 프로필·의존성을 따로 준비한다. 개인 .env나 node_modules를 자동 복사/연결하지 않는다.
세션 기록은 .runtime/sessions에 저장하며, 공유할 목표·검증·이어갈 상태는 docs/tasks의 인수인계에도 남긴다.

## 두 작업을 합친 검토 공간

각 작업을 의도한 커밋으로 보존한 뒤 다음을 실행한다. 브랜치 이름은 예시다.

```sh
python3 tools/harness/run.py integration prepare combined --target harness/first --source harness/second --goal "두 사용자 요구를 유지한 통합" --acceptance "첫 작업의 요구 유지" --acceptance "두 번째 작업의 요구 유지"
python3 tools/harness/run.py integration status combined
python3 tools/harness/run.py integration check combined --plan
python3 tools/harness/run.py integration check combined
```

prepare는 공통 원본·양쪽 커밋·변경 경로·중복 경로를 기록하고 .worktrees/integration-<이름>에 별도 detached worktree를 만든다.
그곳에서 source를 --no-commit으로 합친다. target 브랜치나 원래 작업 폴더에는 병합하지 않는다.
Git hook과 기록된 rerere 자동 해결을 끄고, 충돌이 있으면 그대로 보존해 needs_resolution으로 보고한다.
같은 파일이라도 겹치지 않는 변경은 Git이 합칠 수 있다. prepared는 의미상 옳다는 판정이 아니다.

.runtime/integrations/<이름>/review.md에서 양쪽 의도·변경별 처리·공유 경계·수용 기준을 검토한다.
충돌은 검토용 worktree에서 해결한다. 해결한 파일의 Git unmerged 상태도 해소해야 검사가 가능하다.
어느 쪽 요구를 유지/조합/제외했는지 이유와 근거를 기록하고, 유효한 요구가 양립하지 않으면 선택 전에 사용자에게 알린다.

check는 양쪽 작업의 변경 경로와 검토 중 추가 변경을 합쳐 checkpoint=integration으로 등록 검사를 실행한다.
--project로 해당 프로젝트 프로필을 지정하고, 필요한 전체 검사는 --full로 요청한다.
해결하지 않은 충돌·남은 conflict marker·diff 오류를 먼저 차단한다.
입력 ref/체크아웃이 바뀌거나 검사 중 통합 소스가 바뀌면 stale로 다룬다. 새 입력으로 다시 준비/검토한다.
등록 검사 통과는 checks_passed_review_pending이며 review_required=true, product_accepted=false다.
실제 변경 의도·수용 기준 검토가 남았다는 뜻이며 도구가 설계 합의를 자동 승인하지 않는다.

검토용 worktree와 실패 로그는 자동 삭제하지 않는다. 최종 브랜치 반영·커밋·정리는 별도 작업으로 다룬다.
검토 이후 실제 반영할 상태가 달라지면 과거 검증 결과를 그대로 적용하지 않는다.

## 비용과 안내

검증 시점은 [검증 명세](verification.md)의 checkpoint/run_at을 사용한다.
작업 시작에 의미 있는 작업 묶음·검증 범위·E2E 수행 여부와 시점을 사용자에게 알린다.
도구의 범위 계산은 파일 규칙이며 의미상 의존성 분석이나 모든 세션의 동시 수정 방지 기능은 아니다.
