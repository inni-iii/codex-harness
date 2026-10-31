# 새 프로젝트에 맞는 워크플로 연결

주제가 정해진 뒤 이 문서를 읽는다. 지금은 특정 앱·프레임워크를 생성하지 않는다.

## 설정 순서

1. project 명령으로 문서 인덱스·개요·보안 설계 양식과 draft 프로필을 만든다. `docs/projects/README.md`에 실제 프로젝트 인덱스의 링크를 연결한다.
2. 프로젝트 개요에 사람이 정한 Charter·아키텍처 경계·마일스톤과 기존 결정/미결정을 적는다. [프로젝트 진행](project-lifecycle.md)에 따라 요구·성공 조건·현재 갭·작업을 연결한다. 작으면 개요 안에서 관리한다.
3. 실제 코드 위치·manifest·잠금 파일·실행 스크립트를 확인하거나 요청 범위 안에서 만든다.
4. security.md의 보호 자원·신뢰 경계·허용 행동·검증 조건을 실제 요구로 채우고, workflow.toml의 context에 프로젝트 규칙·계약·디자인 문서 위치를 연결한다. 보안 절차는 [security-review](../../security-review/SKILL.md)를 따른다.
5. 실제로 실행 가능한 checks를 등록하고 공유 변경의 impacts와 저렴한 전체 연결 스모크를 정의한다.
6. 실제 명령·전제·경로를 확인한 후 state를 active로 바꾼다. 보안 설계는 [단계·범위별 판정](../../../../tools/harness/docs/project-workflows.md#동시-작업의-미결-범위와-완료-판정)으로 병렬 보완하고 관련 미결은 완료로 취급하지 않는다. 명령 구성이 미완성인 프로젝트 draft는 검사 통과로 취급되지 않는다.
7. --project로 확인하고 해당 프로젝트를 기본으로 쓸 때만 tools/harness/harness.toml의 [project].workflow에 등록한다.

```sh
python3 tools/harness/run.py project demo --goal "실제 프로젝트의 목표"
python3 tools/harness/run.py context --kind plan --project docs/projects/demo/workflow.toml --read
python3 tools/harness/run.py check --project docs/projects/demo/workflow.toml --plan
```

명령은 프로젝트가 결정됐을 때 실행하는 예시다.
[프로필 템플릿](../assets/project-workflow.toml), [설정 명세](../../../../tools/harness/docs/project-workflows.md)를 따른다.

## 자료를 어디에 둘지

- index.md: 주제·단계별 정본과 읽을 조건. [프로젝트 진행](project-lifecycle.md)의 다음 행동을 해당 task/계약에 연결한다.
- brief.md: Charter·아키텍처 경계·마일스톤·합의·열린 질문과 계획 정본 위치
- 계획이 실제로 필요하면: 요구·성공 조건·현재 근거·갭·작업의 연결. 인덱스와 관련 context 규칙에서 읽도록 연결하고 개요와 중복 관리하지 않는다.
- security.md: 그 프로젝트의 보호 자원·권한·위협 모델·검증 조건·미해결 위험. 생성 직후는 미작성 초안이다.
- 프로젝트 문서: 도메인 규칙, API 계약, 디자인 기준, 운영 조건 중 실제 필요한 내용
- workflow.toml: 문서 연결과 검증 명령·조건. 비밀값·개인 절대경로는 넣지 않는다.
- task.json/notes.md: 한 작업의 목표·진행·근거·실패·다음 행동
- 공통 스킬: 다음 프로젝트에도 적용할 판단·절차·실패 조건만 유지

필수 `context.documents`에 긴 설계·운영·전체 위키 본문을 모두 넣지 않는다. 기본 인덱스·개요·보안 맥락은 유지하고 상세 문서는 실제 관련 종류/주제/경로 규칙으로 연결한다.
인덱스의 링크는 자동 확장되지 않으므로 선택한 원문을 직접 읽거나 해당 읽기 규칙으로 다시 선택한다.

예: “게시물 공개는 작성자만 가능”은 프로젝트 규칙이다. “변경된 권한 경계는 비소유자 요청도 검사”는 범용 검증 규칙이다.

설치 명령이 성공했다는 것과 앱 실행·MCP 연결·제품 흐름이 검증됐다는 것을 구분한다.
다른 노트북에서는 레포의 잠금 파일과 안내로 설치하고 로컬 인증·환경은 따로 준비한다.
