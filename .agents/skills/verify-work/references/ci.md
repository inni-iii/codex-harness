# 로컬 검사와 CI 연결

GitHub Actions 등 CI를 추가·변경하는 요청에서 읽는다. 배포 자동화는 별도 작업이다.

기존 workflow, manifest, 잠금 파일, Makefile과 실제 검증 명령을 먼저 확인한다.
CI가 호출할 명령은 로컬에서 실행 가능한 동일 진입점에 연결한다.
하네스 검사만 있는 상태에 앱 검증이 있는 것처럼 green no-op job을 만들지 않는다.

## 선택할 항목

- PR/브랜치 trigger와 실제 필요한 검사
- 정적 검사·행동 검사·통합/E2E의 분리와 실행 조건
- 잠금 파일 기반 설치, 테스트 환경·fixture·결과 보존
- 최소 permissions, 동시 실행·오래된 실행 취소
- 필수 check가 항상 상태를 보고하는지
- 의존성 캐시 키가 manifest/lock/runtime 변경을 반영하는지

외부 작업 설정은 현재 공식 action 문서에서 버전·입출력을 확인한다.
untrusted PR 코드를 운영 credential·privileged runner·운영 DB와 연결하지 않는다.
self-hosted runner나 pull_request_target은 일반 PR CI와 같은 권한이라고 가정하지 않는다.
경로 필터로 required workflow가 아예 실행되지 않아 대기 상태에 남는 경우를 확인한다.

실패한 작업의 원본 로그·보고서를 보존하되 환경변수·토큰·테스트 개인정보를 artifact로 내보내지 않는다.
빌드·테스트 결과가 배포 성공이나 제품 수용을 뜻하지 않는다.
SSH 서버에서는 설치·빌드·검사·배포를 실행하지 않는다.
현재 하네스에는 GitHub 배포 workflow를 추가하지 않았다.
