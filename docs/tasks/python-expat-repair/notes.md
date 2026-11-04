# Python Expat 환경 복구

2026-11-04 사용자 수정 요청. 실제 네이티브 훅 실패 원인은 여전히 미확정이며, 이번 범위는 앞서 직접 재현한 기본 Python XML 파서 환경 오류다.

- F1: 기본 Python 3.14.7의 pyexpat가 /usr/lib/libexpat.1.dylib를 로드하나 _XML_SetAllocTrackerActivationThreshold 심볼이 없어 import가 실패한다. 설치된 Homebrew Expat 2.8.4로 임시 연결 시 import가 성공한다.
- 정상 기대: 환경변수 지정 없이 pyexpat import, 정상 XML 파싱, 잘못된 XML 거부가 동작한다.
- 수정 범위: 기본 Python 3.14.7의 pyexpat 한 파일. 원본 백업 후 복사본의 라이브러리 연결 변경과 ad-hoc 서명을 검증하고 적용한다. Python 3.12와 OS 라이브러리·전역 셸 설정·Codex 신뢰 설정은 변경하지 않는다.
- 검증: 수정 전후 동일 Python XML 시나리오, doctor, 관련 훅/JUnit 회귀. 앱 UI/프론트 변경이 없어 브라우저 E2E 비적용.
- 과거 원문: 양쪽 전체 기록 경로를 재검색했다. Claude 2026-10-30 08:55 UTC 원문에도 같은 pyexpat 심볼 오류가 있었고, Codex 이전 원문은 앞선 진단에서 읽은 내용을 재사용했다. Claude plans 디렉터리는 없고 Codex archived_sessions에 JSONL 원문은 없었다.

## 적용과 검증

복사본에서 install_name_tool로 Expat의 연결 경로만 변경하고 ad-hoc 서명·검증, 별도 Python 프로세스 XML 스모크를 통과했다. 사용자 실행 권한 승인 후 설치 모듈 한 파일을 원자 교체했다. 원본과 수정본·설치 SHA-256, 전후 프로세스 stdout/stderr는 .runtime/python-expat-repair/manifest.json에 있다. 임시 DYLD/PYTHON 환경변수 없이 import와 정상/오류 XML 처리가 통과했고 doctor는 JUnit XML parser: available이다.

등록된6개 이벤트 stdin 스모크는 모두 exit0·유효JSON. 첫 check --full --checkpoint final의 모든 등록 검사와 Python407개가 통과했으나 실행 중 이 task.json 근거 연결이 바뀌어 보고서는 stale이다. 소스 차이가 task.json 하나임을 대조했고 같은 기록을 고정한 상태로 최종 검사를 새로 실행한다. skip1은 기존 sandbox의 프로세스 그룹 신호 거부 하위 사례이며 XML/훅 사례는 skip되지 않았다.

설치된 Python 환경의 복구이며 레포 하네스 코드·훅 설정·전역 셸 환경은 변경하지 않았다. Python 재설치/업그레이드 시 동일 라이브러리 불일치가 재발하는지는 별도 점검해야 한다. 현재 대화창의 네이티브 훅 실패 원인은 오류 원문이 없어 아직 미확정이다.

최종 check --full --checkpoint final --reuse 보고서 .runtime/checks/2b31a37b2cb444dfb4fc5c15e1f964cc/report.json은 passed이다. Python407개 실행·실패0·skip1, doctor/agent-config/secret-patterns 통과. 검사 소스는 고정 상태였으며 결과 캐시는 재사용되지 않았다.6개 stdin 이벤트도 모두 통과했다. 자체 검토이며 환경 오류를 레포 코드 결함으로 기록하지 않았다.
