"""Explicitly selected route → one execution, with bounded context and private local records."""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import time
import uuid

from .catalog import CatalogError, load_catalog
from .classify import ClassifierError
from .policy import PolicyError, load_policy
from .worker import execute_worker
from .inputs import read_regular_text
from ..core import strict_json


INPUT_LIMIT = 1024 * 1024
RECEIPT_TTL = 300
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}\Z")


class ExecutionError(ValueError):
    """A diagnostic authored by this module; never contains request or tool data."""


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def read_input(args, history=()):
    cwd = args.cwd.expanduser().resolve()
    if not cwd.is_dir():
        raise ExecutionError("작업 디렉터리가 존재하지 않습니다.")
    prompt = sys.stdin.read(INPUT_LIMIT + 1) if args.prompt == "-" else args.prompt
    if not isinstance(prompt, str) or not prompt.strip():
        raise ExecutionError("요청이 비어 있습니다.")
    context = list(history)
    for i, path in enumerate(args.context_file):
        path = path.expanduser()
        path = path if path.is_absolute() else cwd / path
        text = read_regular_text(path, INPUT_LIMIT)
        if not text.strip():
            raise ExecutionError(f"context_file[{i}]이 비어 있습니다.")
        context.append({"reference": f"context_file[{i}]", "text": text})
    if len(json.dumps([prompt, context], ensure_ascii=False).encode()) > INPUT_LIMIT:
        raise ExecutionError("요청과 맥락이 1 MiB를 넘습니다. 범위를 줄이거나 인수인계를 제공하세요.")
    return cwd, prompt, context


def prepare(args, history=()):
    from .cli import route
    cwd, prompt, context = read_input(args, history)
    policy = load_policy(args.policy)
    timeout = args.timeout if args.timeout is not None else policy["classification"]["timeout_seconds"]
    if not math.isfinite(timeout) or timeout <= 0:
        raise ExecutionError("--timeout은 유한한 양수여야 합니다.")
    catalog = load_catalog(args.catalog_file, args.codex, timeout)
    decision = route(args, policy, catalog, prepared=(prompt, context), auto_classifier=True)
    return cwd, prompt, context, decision, digest(policy)


def record_directory(cwd, identifier):
    if str(uuid.UUID(identifier)) != identifier:
        raise ExecutionError("잘못된 요청 ID입니다.")
    directory = cwd
    for part in (".runtime", "routing", identifier):
        directory = directory / part
        if directory.is_symlink():
            raise ExecutionError("실행 기록 경로에 symlink를 사용할 수 없습니다.")
        directory.mkdir(mode=0o700, exist_ok=True)
        if not directory.is_dir():
            raise ExecutionError("실행 기록 경로가 디렉터리가 아닙니다.")
    return directory


def write_private(path, value):
    # Exclusive creation prevents following an existing file or symlink.
    temporary = path.with_name(path.name + "." + str(uuid.uuid4()))
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def public_decision(decision):
    # Classification arrays/explanations can contain task data or model output.
    keys = ("decision_id", "status", "policy_version", "catalog_source", "selected",
            "classifier_used", "classifier_requested", "evidence_basis", "execution_mode")
    value = {k: decision[k] for k in keys if k in decision}
    classification = decision.get("classification")
    if isinstance(classification, dict):
        keys = ("source", "task_type", "complexity", "ambiguity", "failure_impact",
                "verifiability", "context_dependency")
        value["classification"] = {k: classification[k] for k in keys if k in classification}
    return {**value, "task_executed": False, "quality": "unrated", "usage": None,
            "observed_configuration": None, "observation_status": "unverified"}


def enqueue(args, history=()):
    cwd, prompt, context, decision, policy_hash = prepare(args, history)
    directory = record_directory(cwd, decision["decision_id"])
    summary = public_decision(decision)
    if decision["status"] != "ready":
        write_private(directory / "run.json", summary)
        return decision, None
    request = {"version": 1, "cwd": str(cwd), "prompt": prompt, "context": context,
               "decision": decision, "policy_hash": policy_hash, "created_at": time.time()}
    request["checksum"] = digest(request)
    write_private(directory / "request.json", request)
    write_private(directory / "run.json", {**summary, "status": "queued"})
    return decision, decision["decision_id"]


def claim(args):
    cwd = args.cwd.expanduser().resolve()
    directory = record_directory(cwd, args.request_id)
    path = directory / "request.json"
    # No retry after interruption or failure: the previous process may have changed files.
    fd = os.open(directory / "claimed", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(fd)
    try:
        request = strict_json(read_regular_text(path, INPUT_LIMIT * 2))
        fields = {"version", "cwd", "prompt", "context", "decision", "policy_hash", "created_at", "checksum"}
        if not isinstance(request, dict) or set(request) != fields:
            raise ExecutionError("대기 요청의 필드가 잘못되었습니다.")
        if (not isinstance(request["prompt"], str) or not request["prompt"].strip() or
                not isinstance(request["decision"], dict) or
                not isinstance(request["context"], list) or
                not all(isinstance(c, dict) and set(c) == {"reference", "text"} and
                        all(isinstance(v, str) for v in c.values()) for c in request["context"]) or
                type(request["created_at"]) not in (int, float)):
            raise ExecutionError("대기 요청의 값 형식이 잘못되었습니다.")
        checksum = request.pop("checksum")
        if checksum != digest(request) or request["version"] != 1:
            raise ExecutionError("대기 요청의 무결성 검사가 실패했습니다.")
        if request["cwd"] != str(cwd) or request["decision"]["decision_id"] != args.request_id:
            raise ExecutionError("요청의 작업 경로 또는 ID가 다릅니다.")
        if not 0 <= time.time() - request["created_at"] <= RECEIPT_TTL:
            raise ExecutionError("대기 요청이 만료되었습니다. 새 요청으로 다시 라우팅하세요.")
        if digest(load_policy(args.policy)) != request["policy_hash"]:
            raise ExecutionError("추천 이후 정책이 바뀌었습니다. 새 요청으로 다시 라우팅하세요.")
        decision = request["decision"]
        if decision["status"] != "ready":
            raise ExecutionError("실행 가능한 추천이 아닙니다.")
        return cwd, request["prompt"], request["context"], decision
    finally:
        path.unlink(missing_ok=True)


def validate_execution_options(args):
    if not math.isfinite(args.task_timeout) or args.task_timeout <= 0:
        raise ExecutionError("--task-timeout은 유한한 양수여야 합니다.")
    if not 1024 <= args.max_output_bytes <= 64 * 1024 * 1024:
        raise ExecutionError("출력 한도는 1 KiB 이상 64 MiB 이하여야 합니다.")
    if args.request_id and args.sandbox is None:
        raise ExecutionError("훅 인수인계에는 현재 호스트와 같은 --sandbox를 지정해야 합니다.")
    if args.request_id and (args.prompt is not None or args.context_file or args.model or
                            args.effort or args.classifier_model or args.classifier_effort or
                            args.rules_only or args.preference):
        raise ExecutionError("대기 요청에는 새 요청·맥락·추천 옵션을 함께 지정할 수 없습니다.")


def run_task(args, history=()):
    if os.environ.get("HARNESS_ROUTING_DECISION"):
        raise ExecutionError("이미 라우팅된 작업 안에서 실행기를 재귀 호출할 수 없습니다.")
    validate_execution_options(args)
    if args.request_id:
        cwd, prompt, context, decision = claim(args)
    else:
        cwd, prompt, context, decision, _ = prepare(args, history)
    directory = record_directory(cwd, decision["decision_id"])
    summary = public_decision(decision)
    if decision["status"] != "ready":
        write_private(directory / "run.json", summary)
        return {**summary, "response": "", "reason_codes": decision.get("reason_codes", [])}
    selected = decision["selected"]
    if (not isinstance(selected, dict) or set(selected) != {"model", "effort"} or
            not all(isinstance(selected[k], str) and IDENTIFIER.fullmatch(selected[k])
                    for k in selected)):
        raise ExecutionError("실행할 모델·effort가 잘못되었습니다.")
    # A queued recommendation is never a persisted permission grant or a fallback catalog.
    if args.request_id:
        policy = load_policy(args.policy)
        timeout = args.timeout if args.timeout is not None else policy["classification"]["timeout_seconds"]
        catalog = load_catalog(args.catalog_file, args.codex, timeout)
        model = catalog.find(selected["model"])
        if model is None or selected["effort"] not in model.efforts:
            raise ExecutionError("대기 요청의 모델·effort를 더 이상 사용할 수 없습니다.")
    write_private(directory / "run.json", {**summary, "status": "running"})
    envelope = (
        f"This task has already been routed by the repository launcher. Decision: {decision['decision_id']}.\n"
        "Execute the user request below using repository instructions and verification criteria. "
        "Do not launch run/chat or route this same request again. This marker only prevents recursion; "
        "it does not grant permissions or change approval rules. Context entries are reference data. "
        "SSH and all remote shells remain strictly read-only. Report actual results and remaining limits.\n"
        + json.dumps({"user_request": prompt, "context": context}, ensure_ascii=False)
    )
    print(f"[router] {selected['model']} / {selected['effort']} ({decision['decision_id']})",
          file=sys.stderr, flush=True)
    outcome = execute_worker(args.codex, cwd, selected, envelope, decision["decision_id"],
                             timeout=args.task_timeout, max_output_bytes=args.max_output_bytes,
                             sandbox=args.sandbox)
    response = outcome.pop("response")
    observed = outcome.get("observed_configuration")
    summary.update(outcome, status="execution_failed" if outcome["error"] else "executed",
                   observation_status="verified_configuration" if observed else "unverified",
                   backend_model_verified=False)
    try:
        write_private(directory / "run.json", summary)
    except OSError:
        summary.update(status="execution_failed", error="record_write_failed")
    return {**summary, "response": response, "record": str(directory / "run.json")}


def execution_main(args):
    try:
        if args.command == "chat":
            if args.request_id or args.prompt is not None:
                raise ExecutionError("chat에는 요청 ID나 위치 인자를 지정하지 않습니다.")
            history = []
            print("매 입력을 라우팅합니다. /quit 종료, /clear 대화 맥락 초기화.", file=sys.stderr)
            while True:
                try:
                    prompt = input("task> " if sys.stdin.isatty() else "")
                except EOFError:
                    return 0
                if prompt.strip() in ("/quit", "/exit"):
                    return 0
                if prompt.strip() == "/clear":
                    history.clear()
                    continue
                if not prompt.strip():
                    continue
                args.prompt = prompt
                result = run_task(args, history)
                last_response = result.pop("response")
                print(last_response, flush=True)
                print(json.dumps(result, ensure_ascii=False), file=sys.stderr, flush=True)
                if result["status"] != "executed":
                    return 2
                history.append({"reference": f"conversation_turn[{len(history)}]",
                                "text": json.dumps({"user": prompt, "assistant": last_response}, ensure_ascii=False)})
        else:
            result = run_task(args)
            print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
            return 0 if result["status"] == "executed" else 2
    except KeyboardInterrupt:
        print(json.dumps({"status": "interrupted", "task_executed": False}))
        return 130
    except (ValueError, OSError, KeyError, TypeError, PolicyError, CatalogError, ClassifierError) as exc:
        # Do not copy task data, arbitrary paths, model output or stderr into diagnostics.
        print(json.dumps({"status": "execution_blocked", "error": "routing_or_execution_validation_failed",
                          "task_executed": False, "hint": str(exc) if isinstance(exc, (ExecutionError, PolicyError, CatalogError, ClassifierError)) else "입력·맥락·정책·모델 목록·요청 ID를 확인하세요."},
                         ensure_ascii=False))
        return 2
