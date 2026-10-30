# 보안 검사기 반복 검토 기록

2026-10-31 KST. 이 기록 절차가 다른 세션에서 추가되기 전 이미 확인·수정한 재현을 소급 등록한다. 수정 전의 코드는 승인된 로컬 사본에서 재실행하며 공유 원본을 되돌리지 않는다.

## 확인한 결함

F1: macOS 대소문자 파일 별칭으로 인증 미결이 빠짐. 실제 파일 이름으로 정규화한다.
F2: ./·중복 슬래시가 있는 glob이 적용되지 않고 승인됨. 비정규 패턴을 거부한다.
F3: 계획 직후 보안 문서 변경을 새 버전 통과로 기록함. 계획 전 지문·실행 전후 재검토로 stale 처리한다.
F4: JUnit DTD/과도한 깊이의 파싱을 허용함. 크기·깊이·노드·DTD 제한을 적용한다.
F5: 기본 runtime symlink를 통해 레포 밖으로 기록함. 기본 결과 경로의 링크를 거부한다.
F6: 추적한 build 내부 소스가 지문에서 제외됨. 추적 입력과 사본 inventory를 보존한다.
F7: 압축본에서 .env.example의 합성 키가 누락됨. 예제·명시적 입력을 검사한다.
F8: 지문에서 제외된 기존 소스를 넓은 경로 검사로 덮음. 해당 입력은 설정 필요로 남긴다.
F9: 메타데이터 hook이 상태 필드의 임의 객체를 복사함. 허용한 상태 문자열만 처리한다.
F10: 새 실행/지식 설정의 검사 선택 누락. hook·도구 manifest·학습 catalog를 행동 회귀에 연결한다.
F11: FIFO를 일반 소스로 읽으면 무한 대기함. 일반 파일만 읽고 hash/원본 검증도 같은 경계를 적용한다.

## 검증 범위와 한계

실제 제품이 없어 제품 E2E·실제 모델의 prompt injection 평가는 수행하지 않았다. 합성 키·로컬 fixture만 사용한다. 실제 advisory 조회 ENOTFOUND와 그룹 신호 권한 제한은 발견 없음/자손 정리 완료로 바꾸지 않는다.

## 병렬 작업

다른 세션의 신규 스킬·검증 계약·라우터·학습 기능 변경은 보존한다. 공유 폴더의 중간 상태가 실패하면 실제 통합 실패로 남기고, 이미 통과한 격리 버전을 현재 원본의 통과로 승격하지 않는다.

F12: unittest의 여러 실패 subTest가 부모 테스트 수보다 많을 때 정상적인 실패 보고서를 invalid로 오인했다. FAILED의 실패 이벤트 수를 지원하며 OK의 모순 집계는 계속 거부한다.

수정 전 parsed 보고서: [{"name": "before-core", "report": "/Users/inni/inni/test/codex-harness/.runtime/security-convergence-proofs/before-core/.runtime/checks/f71166659e71429995b50913054a2556/report.json", "status": "failed", "cases": ["test_case_aliases_on_case_insensitive_filesystems_cannot_bypass_security", "test_noncanonical_patterns_cannot_silently_remove_pending_scope", "test_review_change_immediately_after_planning_cannot_be_a_current_pass", "test_xml_declarations_depth_and_node_budget_fail_before_unbounded_parsing", "test_default_runtime_symlink_is_rejected_before_execution", "test_tracked_source_under_artifact_directory_participates_in_cache_and_evidence", "test_environment_template_is_scanned_in_source_archives_without_echoing_secret", "test_excluded_existing_sources_are_not_silently_covered_by_a_broad_check", "test_nonregular_inputs_are_rejected_without_waiting_for_a_writer", "test_failed_subtests_are_real_failures_not_invalid_runner_reports"]}, {"name": "before-integration", "report": "/Users/inni/inni/test/codex-harness/.runtime/security-convergence-proofs/before-integration/.runtime/checks/d651419f341d4f07ba49a178ae7faa85/report.json", "status": "failed", "cases": ["test_metadata_hook_rejects_payloads_hidden_inside_status", "test_execution_and_knowledge_configuration_select_behavioral_regressions"]}]
