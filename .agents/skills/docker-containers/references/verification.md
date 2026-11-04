# 컨테이너 검증과 실패 진단

구성 작성/변경 후 또는 이미지·기동·준비·통신·저장 실패를 조사할 때 읽는다. 필요한 실제 앱/DB/E2E 절차는 소유 스킬로 연결한다.

## 검사 계획과 실행 경계

먼저 사용자 요구에서 성공·오류·복구·권한·격리 사례를 고른다. 읽기 요청에는 config·선택한 상태/로그·파일 대조로 답하고, build/start/exec/설치를 자동 추가하지 않는다. 허용된 구성 변경이면 필요한 로컬 검증을 이어가며 이미 승인한 단계를 다시 묻지 않는다.

대상 Docker context/endpoint가 로컬인지, Compose file/project·volume이 이번 작업 것인지 확인한다. 로컬 CLI가 remote endpoint를 가리킬 수 있다. SSH 서버에서 검사·build·캐시 생성·exec·migration은 금지다. docker exec는 임의 프로세스 실행이므로 단순 상태 조회로 취급하지 않는다.

## 단계별 근거

| 단계 | 실제 확인 | 그 결과만으로 주장하지 않을 것 |
|---|---|---|
| 정적 | manifest/lock·경로·ignore·설정 merge·Compose config·누락 입력 | 이미지 build/기동/제품 동작 성공 |
| build | 실제 context/플랫폼/lock·build script·최종 runtime·image ID | 기존 volume에서 데이터 복구·브라우저 흐름 성공 |
| 기동 | 이번 project의 상태·health·종료 코드·시간 제한 | 업무 기능 전체 성공 |
| 기능 | frontend→API→DB 저장/재조회, 필요한 오류/권한 흐름 | 다른 서비스·운영 트래픽의 완전한 품질 |
| 복구/격리 | 재시작 후 데이터 유지, 연결 복구, 두 실행의 이름/포트/volume 독립, timeout 정리 | backup 파일만으로 복원 성공 |
| 복원 | 별도 합성/격리 DB로 복원 후 실제 재조회 | 운영 복구 승인·현재 운영 데이터 변경 권한 |

config 전체 출력은 보간된 비밀값을 포함할 수 있다. 조용한 validation 또는 비밀을 제외한 필드만 사용한다. 예를 들어 실제 CLI 지원을 확인한 뒤 **정적 원문 구조**에는 `--env-file /dev/null`, `config --no-interpolate --no-env-resolution --quiet`를 사용할 수 있다. 이는 실제 환경 변수/secret/경로/프로필의 유효성 검사를 생략한 결과다. 이후 허용된 환경에서 필수 입력 누락/경로/서비스 선택을 별도로 확인한다. 옵션 미지원은 환경/버전 문제로 남기며 검사를 통과로 꾸미지 않는다.

대상 앱의 공식 build/test 명령을 사용하고 Compose/E2E 결과를 workflow checks로 연결한다. fixture/config 검사·하네스 자체 테스트를 실제 앱 E2E로 대체하지 않는다. UI 기능이 포함되면 실제 브라우저에서 결과를 얻는 흐름으로 검증한다.

## 원인을 분리한다

| 관측 | 좁힐 대상 |
|---|---|
| Dockerfile/COPY not found | 기준 경로·context·ignore·생성 산출물·대소문자 |
| registry/설치 실패 | 인증/네트워크/버전·architecture·실행 정책. 비밀을 출력하지 않음 |
| command/모듈/lib 실행 실패 | 최종 이미지 산출물·PATH·native 의존성·entrypoint/command 관계 |
| unhealthy/start timeout | 실제 health 도구·endpoint·schema/DB 권한·준비 시간 |
| connection refused/DNS | browser/public/server URL·localhost·서비스 network·프로필·listen 주소 |
| permission denied | 이미지 USER·volume uid/gid·read-only root·writable 경로. privileged로 우회하지 않음 |
| port/name/network conflict | 다른 실행 소유권·고정 이름·포트·external 자원. 다른 서비스를 내리지 않음 |
| 재시작 뒤 데이터 없음 | 실제 PGDATA·volume 이름/마운트·초기화·메이저 버전 |
| OOM/느림 | VM/컨테이너 한도·실측 피크·worker/pool·emulation·디스크. 무조건 자원 증설하지 않음 |

읽기 전용 조회의 실패, daemon socket 차단, 명령 timeout, 실행 수 0·모두 skip을 구분한다. 실패 로그에서 비밀·실데이터를 제외한 최소 구간을 보존한다. 검사 우회나 destructive cleanup으로 초록 상태를 만들지 않는다.

## 완료 보고

변경 파일, 대상 repo/cwd·Compose 조합·project·플랫폼·소스/lock·image 식별자, 실행 명령·종료 코드·검사 수/실패/skip, 데이터/자원 보존과 남은 미확인을 기록한다. 정상·오류·복구·소유권에서 최종 재검토하고 발견 사항과 회귀를 보존한다. 진단만 했다면 수정/재시작을 했다고 쓰지 않는다.

예: 예제 Compose config가 통과해도 존재하지 않는 frontend Dockerfile이나 build context는 별도 경로 대조로 발견해야 한다. 실제 secret 없이도 현재 `.env` 존재·COPY·ignore를 대조해 이미지 포함 위험을 지적할 수 있지만, 배포 이미지에서 노출을 실측했다고 보고하지 않는다.
