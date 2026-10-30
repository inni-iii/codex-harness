# 서비스 자료

실제 프로젝트의 요구사항·도메인 규칙·설계·결정과 작업 기록을 모은다.
아직 서비스 주제와 코드 위치는 정해지지 않았다.

문서를 찾을 때는 [문서 인덱스](index.md)에서 이번 질문·단계에 맞는 하위 지도와 원문을 고른다.

| 위치 | 내용 |
| --- | --- |
| [projects/](projects/README.md) | 주제별 개요·규칙·설계·workflow.toml |
| `tasks/<작업명>/` | task.json의 목표·완료 기준과 notes.md의 근거·인수인계 |
| `knowledge/catalog.json` | 프로젝트/공통 교훈의 조건·근거·검토·대체 기록. [관리 방법](../tools/harness/docs/knowledge.md) |

프로젝트와 작업 기록은 다음 명령으로 만든다. 현재 `tasks/`에는 하네스 자체의 작업 기록이 있다.
아래 이름과 목표는 실제 프로젝트가 정해졌을 때 바꾸는 예시다. 명령은 레포 루트에서 실행한다.

```sh
python3 tools/harness/run.py project demo --goal "프로젝트 목표"
python3 tools/harness/run.py task first-feature --kind implement --goal "첫 사용자 흐름" --acceptance "결과와 오류 복구를 확인한다"
```

생성된 workflow.toml은 draft다. 실제 검사·문서 연결을 채운 뒤 활성화한다.
project는 개요·보안 초안·워크플로와 선택 읽기용 `index.md`를 만든다. 설계나 코드까지 자동 생성하지 않는다.
기존 프로젝트나 작업을 덮어쓰지 않는다.

범용 작업 지침은 [.agents](../.agents/README.md), 하네스 설명과 구현 근거는
[tools/harness](../tools/harness/README.md)에서 관리한다.
인증·비밀값·개인 세션 원문을 공유 자료에 넣지 않는다.
