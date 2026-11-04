# F1: 범위 밖 lifecycle fixture 오류

고정 사본 전체 검사 fbf2483521714da19462aac9390de4d3의 Python478 중 1개 오류/skip1. test_bad_binding_paths_keys_and_runtime_symlinks_do_not_write_outside에서 테스트 준비 중 .runtime가 이미 존재해 symlink_to가 FileExistsError를 냈다. 체크리스트 파일이 아닌 기존 훅/fixture 경계의 오류이며 이번 선택 회귀2개는 통과했다. 소유는 기존 lifecycle/hooks 보강 경로다. 현재 요청에서 해당 코드나 테스트를 임의 수정하지 않고 전체 통과 근거로 사용하지 않는다. 다음 행동은 이 테스트 단독 재현과 .runtime 생성 시점/다른 세션 훅 변경을 대조하는 것이다.

추가 관측: 현재 원본 test_lifecycle_hooks.py에는 task map 잠금으로 생긴 빈 .runtime를 symlink 준비 전에 rmdir하는 처리가 타 세션 변경으로 들어와 있다. 이번 작업은 해당 파일을 수정하지 않았다. 새 고정 사본의 전체 검사를 통해 반영 상태를 확인한다.
