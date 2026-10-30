# 이 레포의 스킬 작성과 검증

개인 전역 스킬이 없어도 이 문서와 레포 도구로 관리한다.
Codex 실행 프로그램의 설치·로그인은 별도이며 개인 홈 경로를 필수 설정에 넣지 않는다.
작업 시작점은 [maintain-skills](../../../.agents/skills/maintain-skills/SKILL.md)다.

## 생성 도구

```sh
python3 tools/harness/run.py skill create example-task --description "실제 적용 작업과 선택 조건" --instructions docs/tasks/example/instructions.md --topic example-task
python3 tools/harness/run.py skill from-knowledge common-lesson example-task --description "검토 지식의 실제 적용 작업"
python3 tools/harness/run.py skill validate example-task
```

두 생성 예는 대안이다. 실제 ID·이름·본문 경로로 바꾼다.
create는 내용을 채운 본문 파일에서 native SKILL.md와 context 등록을 함께 만들며 기존 폴더를 덮어쓰지 않는다.
from-knowledge는 현재 증거 해시가 맞는 adopted 공통 지식만 허용한다. 프로젝트 사실은 공통 스킬로 자동 전환하지 않는다.
생성 후 AGENTS 지도와 실제 사용 시나리오를 검토한다. validate는 이 레포의 최소 frontmatter 형식을 검사하며 일반 YAML 검증기나 행동 평가기는 아니다.
커밋 로그는 선택적 입력이다. Git 이력이 없는 상태에서도 실제 요구·파일·회귀 근거를 사용한다.

## 도구 입력과 등록 계약

중복 판단·적용 범위·본문 작성 절차는 maintain-skills를 따른다. 이 문서는 CLI와 레포 등록 형식의 정본이다.

| 항목 | 현재 도구의 계약 |
|---|---|
| 이름 | 소문자 영문/숫자와 단어 사이 hyphen, 최대64자. 폴더명과 name이 같아야 하며 기존 폴더를 덮어쓰지 않는다. |
| 설명 | 비어 있지 않은 한 줄, 최대1,024자. 생성기는 인용/escape한 YAML 문자열로 쓴다. |
| 본문 | --instructions의 실제 UTF-8 파일. 비어 있지 않은 최대16,000자이며 비밀값 후보와 미완성 표식을 확인한다. 자동 절차 작성 기능은 아니다. |
| 읽기 조건 | --topic/--kind/--path 반복 가능, OR 선택. topic을 생략하면 새 스킬 이름을 사용한다. .agents/context.toml에 등록하며 잘못된 조건/등록 실패 시 생성분을 되돌린다. |
| 조건부 참조 | 담당 스킬 references 안에 두고 본문 링크와 context 참조 조건을 연결한다. 생성 도구가 참조 본문을 자동 작성하지는 않는다. |
| 기존 스킬 편집 | create로 덮어쓰지 않고 원문을 수정한다. AGENTS 지도·관련 안내·등록을 함께 확인하고 doctor/context로 연결을 검사한다. |

validate는 최소 형식 검사, doctor는 등록·참조·링크·TOML/Python 정적 검사, context --read는 선택된 원문 확인이다.
행동 검증은 실제 요청의 정상·실패·경계 사례에서 수행하며 앞의 정적 검사와 구분한다.

```sh
python3 tools/harness/run.py doctor
python3 tools/harness/run.py context --kind plan --topic security-design --read
python3 tools/harness/run.py context --kind review --paths backend/items.py --topic security --read
python3 -m unittest discover -s tools/harness/tests -v
```

전체 테스트는 실행/선택 기능을 바꿨을 때의 예이며 가벼운 문구 수정에 매번 강제하지 않는다.
사용할 클라이언트에서 .agents/skills 발견 여부를 확인한다. context는 강제 주입 hook이 아니다.
시스템 skill-creator는 작성 때 구조·조건부 참조·검증 원칙을 참고한 도구이며 이 레포는 그 파일이나 전역 설치기를 호출하지 않는다.
