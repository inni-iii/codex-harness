"""Portable task artifacts. Evidence presence is not an independent quality judgment."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re

from .core import inside, write_json

KINDS = ["research", "experiment", "design", "implement", "debug", "review"]


def validate(data: dict, *, root: Path | None = None, task_path: Path | None = None,
             allow_missing_runtime=False) -> list[str]:
    errors = []
    if not isinstance(data, dict):
        return ["task must be an object"]
    if data.get("version") not in (1, 2) or data.get("kind") not in KINDS:
        errors.append("unsupported task version/kind")
    if not isinstance(data.get("status"), str) or data["status"] not in {"planned", "in_progress", "needs_revision", "blocked", "complete"}:
        errors.append("invalid task status")
    if not isinstance(data.get("goal"), str) or not data["goal"].strip():
        errors.append("task needs a goal")
    findings = data.get('findings', [])
    if (not isinstance(findings, list) or not all(isinstance(x, str) and x.strip() for x in findings)
            or len(set(findings)) != len(findings)):
        errors.append('confirmed finding IDs must be unique strings')
    criteria = data.get("acceptance")
    if not isinstance(criteria, list) or not criteria:
        return errors + ["task needs acceptance conditions"]
    seen = set()
    for criterion in criteria:
        if not isinstance(criterion, dict):
            errors.append("acceptance condition must be an object")
            continue
        ident = criterion.get("id")
        if not isinstance(ident, str) or not ident or ident in seen:
            errors.append("acceptance IDs must be unique strings")
        else:
            seen.add(ident)
        if not isinstance(criterion.get("condition"), str) or not criterion["condition"].strip():
            errors.append("empty acceptance condition")
        if not isinstance(criterion.get("status"), str) or criterion["status"] not in {"pending", "passed", "failed", "unverified"}:
            errors.append("invalid acceptance status")
        evidence = criterion.get("evidence")
        if not isinstance(evidence, list) or not all(isinstance(x, str) and x.strip() for x in evidence):
            errors.append("evidence must be a list of source references")
        method = criterion.get("method")
        if data.get("status") == "complete" and (criterion.get("status") != "passed" or not isinstance(method, str) or not method.strip() or not evidence):
            errors.append("complete task requires every condition to pass with method and evidence")
    if data.get('version') == 2:
        entries = data.get('evidence')
        if not isinstance(entries, dict):
            errors.append('version-2 task requires a typed evidence object')
        elif any(ref not in entries for c in criteria if isinstance(c, dict) and isinstance(c.get('evidence'), list)
                 for ref in c['evidence'] if isinstance(ref, str)):
            errors.append('acceptance references an unknown evidence ID')
        if isinstance(entries, dict):
            for entry in entries.values():
                if (not isinstance(entry, dict) or entry.get('type') not in {'source', 'artifact', 'check', 'experiment'}
                        or not isinstance(entry.get('path'), str) or not entry['path']
                        or '..' in Path(entry['path']).parts or Path(entry['path']).as_posix() != entry['path']
                        or not isinstance(entry.get('sha256'), str) or not re.fullmatch('[0-9a-f]{64}', entry['sha256'])):
                    errors.append('invalid typed evidence record')
                elif root is not None:
                    try:
                        inside(root, entry['path'])
                    except ValueError:
                        errors.append('evidence path escapes the repository')
    if data.get('status') == 'complete':
        if data.get('version') == 1:
            errors.append('legacy completion lacks verified evidence; migrate to version 2')
        elif root is None or task_path is None:
            errors.append('completed tasks require repository-aware evidence validation')
        elif not isinstance(data.get('review'), dict) or not data['review'].get('path') or not data['review'].get('sha256'):
            errors.append('completed task needs a bound review record')
        elif not errors:
            from .evidence import assess
            errors.extend(assess(root, task_path, data, require_current=False, allow_missing_runtime=allow_missing_runtime))
    return errors


def create(root: Path, slug: str, kind: str, goal: str, acceptance: list[str]) -> Path:
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise ValueError("task name must be a lowercase hyphenated slug")
    if kind not in KINDS or not goal.strip() or not acceptance or not all(x.strip() for x in acceptance):
        raise ValueError("task needs a kind, goal and at least one acceptance condition")
    path = inside(root, f"docs/tasks/{slug}")
    path.mkdir(parents=True, exist_ok=False)
    write_json(path / "task.json", {"version": 2, "kind": kind, "goal": goal, "status": "planned",
               "evidence": {}, "review": None, "findings": [],
               "created_at": datetime.now(timezone.utc).isoformat(), "depends_on": [], "inputs": [],
               "scope": [], "constraints": [], "decisions": [], "open_questions": [],
               "acceptance": [{"id": f"A{i+1}", "condition": text, "method": "", "status": "pending", "evidence": []}
                              for i, text in enumerate(acceptance)], "next_action": "Define the verification method before execution."})
    (path / "notes.md").write_text(
        "# 작업 기록\n\n중요한 발견·실패·정정과 그 근거를 날짜와 함께 기록한다.\n"
        "공통 규칙으로 만들 후보는 적용 조건·제외 조건·재현/회귀 근거를 함께 남긴다.\n"
        "\n## 검증 계획\n\n"
        "- 사용자 결과 기준의 의미 있는 작업 묶음:\n"
        "- 이번 검증 범위·checkpoint와 사용자에게 알린 내용:\n"
        "- E2E 수행 여부·시점·사유와 미룬 검사:\n"
        "- 격리 위치·기준 상태·통합 시 함께 유지할 요구:\n"
        "\n## 확인한 결함과 회귀\n\n"
        "실제 결함을 확인하면 ID·증상·재현 입력·기대 결과·근거를 즉시 적는다. 추측과 환경 오류는 구분한다.\n"
        "수정 전 실패·수정 후 통과·테스트/시나리오 위치·검사 수집 조건·미실행 이유를 보존한다.\n"
        "마지막 수정 뒤의 재검토를 남기고 review.json의 verification.findings/rounds에 연결한다.\n"
        "\n## 인수인계\n\n"
        "- 목표·범위·현재 상태와 이어서 읽을 자료:\n"
        "- 확정 결정·이유·미결정:\n"
        "- 수용 기준별 실제 명령·cwd·대상 상태·결과·근거 위치:\n"
        "- 실패/탈락한 방법·당시 조건·재검토 조건:\n"
        "- 남은 문제·환경 전제:\n"
        "- 다음 한 행동(파일/함수/명령과 관측할 결과):\n\n"
        "다른 노트북에 없는 로컬 로그는 재현 명령도 남긴다. 비밀값·개인 경로는 기록하지 않는다.\n",
        encoding="utf-8")
    return path / "task.json"
