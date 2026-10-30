"""Optional model recommendations and explicitly selected routed execution."""

import argparse
import json
import math
from pathlib import Path
import sys
import uuid

from .catalog import CatalogError, describe, load_catalog
from .classify import ClassifierError, classify_codex, classify_rules
from .policy import PolicyError, load_policy, select_pair


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="python tools/harness/run.py", description="Codex 모델·추론 강도 추천")
    commands = root.add_subparsers(dest="command", required=True)
    for name in ("catalog", "route", "run", "chat"):
        p = commands.add_parser(name)
        p.add_argument("--policy", type=Path, help="초기 정책 대신 사용할 전체 정책 TOML")
        p.add_argument("--catalog-file", type=Path, help="CLI 조회 대신 사용할 raw 모델 목록 JSON")
        p.add_argument("--codex", default="codex", help="Codex 실행 파일 경로")
        p.add_argument("--timeout", type=float, help="목록 조회·분류 호출의 대기 한도(초)")
        if name != "catalog":
            p.add_argument("prompt", nargs="?" if name in ("run", "chat") else None,
                           help="요청 문자열. - 이면 stdin에서 읽음; chat은 매 입력을 자동 라우팅")
            p.add_argument("--cwd", type=Path, default=Path.cwd())
            p.add_argument("--context-file", type=Path, action="append", default=[])
            p.add_argument("--preference", choices=("quality", "balanced", "economy"))
            p.add_argument("--rules-only", action="store_true", help="분류 모델을 호출하지 않음")
            p.add_argument("--classifier-model", help="분류용 모델. 작업용 모델 지정과 별개")
            p.add_argument("--classifier-effort", help="생략하면 분류용 모델의 목록 기본 effort 사용")
            p.add_argument("--model", help="추천할 작업용 모델을 직접 지정")
            p.add_argument("--effort", help="추천할 작업용 effort를 직접 지정")
        if name in ("run", "chat"):
            p.add_argument("--request-id", help="프롬프트 훅에서 준비한 요청을 한 번 실행")
            p.add_argument("--task-timeout", type=float, default=1800,
                           help="실제 작업 프로세스의 전체 대기 한도(초)")
            p.add_argument("--max-output-bytes", type=int, default=8 * 1024 * 1024)
            p.add_argument("--sandbox", choices=("read-only", "workspace-write"),
                           help="명시한 경우에만 적용; 생략하면 기존 Codex 권한 설정 유지")
    return root


def route(args: argparse.Namespace, policy: dict, catalog, *, prepared=None,
          auto_classifier=False) -> dict:
    decision = {"contract_version": "0.1", "decision_id": str(uuid.uuid4()),
                "status": "classification_required", "policy_version": policy["policy_version"],
                "catalog_source": catalog.source, "selected": None, "classification": None,
                "classifier_used": False, "task_executed": False, "missing_context": [],
                "reason_codes": [], "observed_model": None, "observed_effort": None,
                "quality": "unrated", "usage": None}
    prompt = (prepared[0] if prepared is not None else
              sys.stdin.read() if args.prompt == "-" else args.prompt)
    if not prompt.strip():
        raise ValueError("요청이 비어 있습니다.")
    cwd = args.cwd.expanduser().resolve()
    if not cwd.is_dir():
        raise ValueError("작업 디렉터리가 존재하지 않습니다.")
    context = list(prepared[1]) if prepared is not None else []
    for i, path in enumerate([] if prepared is not None else args.context_file):
        path = path.expanduser()
        path = path if path.is_absolute() else cwd / path
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            decision.update(status="needs_context", missing_context=[f"context_file[{i}]을 읽을 수 없습니다."],
                            reason_codes=["CONTEXT_FILE_UNREADABLE"])
            return decision
        if not text.strip():
            decision.update(status="needs_context", missing_context=[f"context_file[{i}]이 비어 있습니다."],
                            reason_codes=["CONTEXT_FILE_EMPTY"])
            return decision
        # Reference indexes identify supplied material without exposing full local paths.
        context.append({"reference": f"context_file[{i}]", "text": text})
    preference = args.preference or policy["default_preference"]
    decision["preference"] = preference
    classification = classify_rules(prompt, context)
    if classification["missing_context"]:
        decision.update(status="needs_context", classification=classification,
                        missing_context=classification["missing_context"], reason_codes=["MISSING_PRIOR_CONTEXT"])
        return decision
    if args.model and not catalog.find(args.model):
        decision.update(status="unavailable", reason_codes=["UNSUPPORTED_MODEL"])
        return decision
    if args.effort and not any(args.effort in m.efforts for m in catalog.models
                               if not args.model or m.id == args.model):
        decision.update(status="unavailable", reason_codes=["UNSUPPORTED_PAIR"])
        return decision
    if args.model and args.effort:
        decision.update(select_pair(catalog, classification, policy, preference, args.model, args.effort))
        decision["classification"] = classification
        return decision
    if classification["complexity"] == "unknown":
        if args.rules_only:
            decision.update(classification=classification, reason_codes=["CLASSIFIER_REQUIRED"])
            return decision
        name = args.classifier_model or policy["classification"]["model"]
        if not name and auto_classifier:
            # Select a classifier from the live catalog and the same reviewed policy.
            # This is a bootstrap role, not a fixed default for the actual task.
            bootstrap = {**classification, "task_type": "answer", "complexity": "low",
                         "ambiguity": "low", "failure_impact": "low"}
            choice = select_pair(catalog, bootstrap, policy, "economy")
            if choice.get("status") != "ready":
                decision.update(status="config_required", reason_codes=["NO_CLASSIFIER_CANDIDATE"])
                return decision
            name = choice["selected"]["model"]
            if not args.classifier_effort and not policy["classification"]["effort"]:
                args.classifier_effort = choice["selected"]["effort"]
        if not name:
            decision.update(status="config_required", classification=classification,
                            reason_codes=["CLASSIFIER_MODEL_REQUIRED"],
                            explanation="분류용 모델을 --classifier-model 또는 정책에 지정해주세요.")
            return decision
        classifier = catalog.find(name)
        effort = args.classifier_effort or policy["classification"]["effort"] or (
            classifier.default_effort if classifier else None)
        if not classifier or not effort or effort not in classifier.efforts:
            decision.update(status="unavailable", reason_codes=["UNSUPPORTED_CLASSIFIER_PAIR"])
            return decision
        decision["classifier_used"] = True
        decision["classifier_requested"] = {"model": name, "effort": effort}
        try:
            classification = classify_codex(prompt, context, args.codex, name, effort,
                                             args.timeout or policy["classification"]["timeout_seconds"])
        except ClassifierError as exc:
            decision.update(status="classifier_error", explanation=str(exc), reason_codes=["CLASSIFIER_FAILED"])
            return decision
    decision["classification"] = classification
    if classification["missing_context"]:
        decision.update(status="needs_context", missing_context=classification["missing_context"],
                        reason_codes=["MISSING_CONTEXT"])
        return decision
    decision.update(select_pair(catalog, classification, policy, preference, args.model, args.effort))
    return decision


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command in ("run", "chat"):
        from .execution import execution_main
        return execution_main(args)
    try:
        policy = load_policy(args.policy)
        timeout = args.timeout if args.timeout is not None else policy["classification"]["timeout_seconds"]
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("--timeout은 유한한 양수여야 합니다.")
        catalog = load_catalog(args.catalog_file, args.codex, timeout)
        value = (describe(catalog, policy["efforts"]) if args.command == "catalog"
                 else route(args, policy, catalog))
    except PolicyError as exc:
        value = {"status": "config_required", "selected": None, "explanation": str(exc), "task_executed": False}
    except CatalogError as exc:
        value = {"status": "unavailable", "selected": None, "explanation": str(exc), "task_executed": False}
    except (ValueError, OSError) as exc:
        value = {"status": "invalid_input", "selected": None, "explanation": str(exc), "task_executed": False}
    print(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if value.get("status", "ready") == "ready" else 2
