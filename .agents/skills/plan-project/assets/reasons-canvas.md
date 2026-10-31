# 기능의 의도와 변경 경계

이 양식은 작성 출발점이다. 아래 예시 metadata·본문·확인 방법을 실제 요구/정본/경로로 교체한다. 이 양식 자체는 승인이나 준비 근거가 아니다.

```json
{
  "version": 1,
  "kind": "reasons-design",
  "profile": "behavioral",
  "requirements": ["R1"],
  "operations": [
    {"id": "O1", "requirements": ["R1"], "paths": ["backend/example.py"], "depends_on": [], "verification": "실제 요구의 정상·오류·경계와 관련 회귀를 확인할 방법"}
  ],
  "decisions": [],
  "references": []
}
```

## Requirements

R1: 누구의 어떤 문제를 해결하고 어떤 관측 결과를 수용할지, 상위 요구·사용자 결정의 정본을 연결한다. 포함/제외 범위와 실패 조건도 적는다.

## Entities

관련 개념·관계·상태·소유/수명·불변식과 기존 정의를 적는다. 새 클래스를 만들라는 뜻은 아니다.

## Approach

선택 방향·대안·탈락 이유·전제와 재검토 조건을 적는다.

## Structure

기존 컴포넌트의 책임·입력/출력·API/데이터/트랜잭션·신뢰 경계와 허용 변경 위치를 적는다.

## Operations

### O1

요구 R1을 제공할 작은 사용자 결과와 입력·선행 조건·산출물·검증 방법을 적는다. 실제 task 수용 기준과 연결한다.

## Norms

관련 AGENTS·언어/보안 규칙의 정본 링크와 이 작업에 필요한 추가 규칙을 적는다. 공통 매뉴얼 전문은 복제하지 않는다.

## Safeguards

보존할 동작·권한·호환성·비용/성능·복구·변경 금지 경계와 이를 확인할 근거를 적는다. 미실행 검사를 통과라고 쓰지 않는다.
