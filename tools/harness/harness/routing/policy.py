"""Inspectable provisional choices, without a fixed worker default."""

from pathlib import Path
import math
import re
import tomllib

from .catalog import Catalog
from .classify import ENUMS


DEFAULT_POLICY = Path(__file__).resolve().parents[2] / "policies" / "policy.example.toml"


class PolicyError(ValueError):
    pass


def load_policy(path: Path | None = None) -> dict:
    try:
        policy = tomllib.loads((path or DEFAULT_POLICY).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise PolicyError("정책 TOML을 읽을 수 없습니다.") from exc
    if set(policy) != {"schema_version", "policy_version", "default_preference", "classification",
                       "efforts", "model_roles", "requirements"}:
        raise PolicyError("정책 필드가 누락되었거나 알 수 없는 필드가 있습니다.")
    if policy["schema_version"] != "0.1" or not isinstance(policy["policy_version"], str):
        raise PolicyError("지원하지 않는 정책 버전입니다.")
    if policy["default_preference"] not in ("quality", "balanced", "economy"):
        raise PolicyError("알 수 없는 선택 선호입니다.")
    c = policy["classification"]
    if not isinstance(c, dict) or set(c) != {"model", "effort", "timeout_seconds"}:
        raise PolicyError("분류 설정 형식이 잘못되었습니다.")
    if not isinstance(c["model"], str) or not isinstance(c["effort"], str):
        raise PolicyError("분류 모델과 effort는 문자열이어야 합니다.")
    timeout = c["timeout_seconds"]
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
        raise PolicyError("분류 대기 한도는 유한한 양수여야 합니다.")
    efforts = policy["efforts"]
    if not isinstance(efforts, dict) or set(efforts) != {"single_agent", "delegating"}:
        raise PolicyError("effort 정책 형식이 잘못되었습니다.")
    for kind in efforts:
        if not isinstance(efforts[kind], list) or not all(isinstance(x, str) and x for x in efforts[kind]):
            raise PolicyError("effort 정책은 문자열 배열이어야 합니다.")
    all_efforts = efforts["single_agent"] + efforts["delegating"]
    if not efforts["single_agent"] or len(set(all_efforts)) != len(all_efforts):
        raise PolicyError("effort 정책이 비었거나 중복됩니다.")
    if not isinstance(policy["model_roles"], list) or not policy["model_roles"]:
        raise PolicyError("모델 역할 정책이 필요합니다.")
    for role in policy["model_roles"]:
        if not isinstance(role, dict) or set(role) != {"pattern", "capability", "priority"}:
            raise PolicyError("모델 역할 형식이 잘못되었습니다.")
        try:
            re.compile(role["pattern"])
        except (re.error, TypeError) as exc:
            raise PolicyError("모델 패턴이 잘못되었습니다.") from exc
        for field in ("capability", "priority"):
            if type(role[field]) is not int or role[field] < 0:
                raise PolicyError("모델 역할의 수치는 음수가 아닌 정수여야 합니다.")
    if not isinstance(policy["requirements"], list) or not policy["requirements"]:
        raise PolicyError("작업 요구 정책이 필요합니다.")
    for rule in policy["requirements"]:
        if not isinstance(rule, dict) or set(rule) != {"id", "when", "capability", "effort"}:
            raise PolicyError("작업 요구 정책 형식이 잘못되었습니다.")
        if not isinstance(rule["id"], str) or not isinstance(rule["when"], dict):
            raise PolicyError("작업 요구 조건 형식이 잘못되었습니다.")
        if not set(rule["when"]) <= {"task_type", "complexity", "ambiguity", "failure_impact", "verifiability"}:
            raise PolicyError("알 수 없는 작업 요구 조건입니다.")
        if not all(isinstance(x, str) for x in rule["when"].values()):
            raise PolicyError("작업 요구 조건값은 문자열이어야 합니다.")
        if not all(v in ENUMS[k] for k, v in rule["when"].items()):
            raise PolicyError("작업 요구 조건값이 분류 형식에 없습니다.")
        if type(rule["capability"]) is not int or rule["capability"] < 0:
            raise PolicyError("요구 능력은 음수가 아닌 정수여야 합니다.")
        if rule["effort"] not in efforts["single_agent"]:
            raise PolicyError("작업 요구 effort가 단일 에이전트 정책에 없습니다.")
    return policy


def select_pair(catalog: Catalog, classification: dict, policy: dict, preference: str,
                model_override: str | None = None, effort_override: str | None = None) -> dict:
    if model_override and not catalog.find(model_override):
        return {"status": "unavailable", "reason_codes": ["UNSUPPORTED_MODEL"]}
    if model_override and effort_override:
        if effort_override not in catalog.find(model_override).efforts:
            return {"status": "unavailable", "reason_codes": ["UNSUPPORTED_PAIR"]}
        mode = ("delegated" if effort_override in policy["efforts"]["delegating"] else
                "single_agent" if effort_override in policy["efforts"]["single_agent"] else "unknown")
        return {"status": "ready", "selected": {"model": model_override, "effort": effort_override},
                "evidence_basis": "user_override", "reason_codes": ["EXPLICIT_PAIR"],
                "explanation": "사용자가 지정한 모델·effort의 목록 지원을 확인했습니다.",
                "execution_mode": mode}
    if any(classification[x] == "unknown" for x in ("complexity", "ambiguity", "failure_impact")):
        return {"status": "classification_required", "reason_codes": ["UNKNOWN_TASK_REQUIREMENTS"]}
    requirement = next((r for r in policy["requirements"]
                        if all(classification.get(k) == v for k, v in r["when"].items())), None)
    if requirement is None:
        return {"status": "config_required", "reason_codes": ["NO_REQUIREMENT_RULE"]}
    order = policy["efforts"]["single_agent"]
    required_effort = order.index(requirement["effort"])
    candidates = []
    rejected = []
    for model in catalog.models:
        if model_override and model.id != model_override:
            continue
        role = next((r for r in policy["model_roles"] if re.fullmatch(r["pattern"], model.id)), None)
        if role is None and model_override:
            role = {"capability": 0, "priority": 0}
        required_modalities = set(classification.get("required_capabilities", [])) & {"text", "image"}
        for effort in model.efforts:
            if effort_override and effort != effort_override:
                continue
            if not model_override and not required_modalities <= set(model.modalities):
                rejected.append({"model": model.id, "effort": effort, "reason": "INPUT_MODALITY_UNVERIFIED"})
                continue
            if role is None:
                rejected.append({"model": model.id, "effort": effort, "reason": "UNREVIEWED_MODEL_ROLE"})
                continue
            if effort in order:
                effort_rank, mode, delegation = order.index(effort), "single_agent", 0
            elif effort in policy["efforts"]["delegating"]:
                effort_rank, mode, delegation = len(order) - 1, "delegated", 1
            else:
                rejected.append({"model": model.id, "effort": effort, "reason": "UNREVIEWED_EFFORT"})
                continue
            ability_gap = 0 if model_override else role["capability"] - requirement["capability"]
            effort_gap = 0 if effort_override else effort_rank - required_effort
            if ability_gap < 0 or effort_gap < 0:
                rejected.append({"model": model.id, "effort": effort, "reason": "BELOW_PROVISIONAL_REQUIREMENT"})
                continue
            if preference == "quality":
                score = (effort_gap, ability_gap, delegation, role["priority"], model.priority, model.id)
            elif preference == "economy":
                score = (ability_gap, effort_gap, delegation, role["priority"], model.priority, model.id)
            else:
                score = (ability_gap + effort_gap, delegation, ability_gap, role["priority"], model.priority, model.id)
            candidates.append((score, {"model": model.id, "effort": effort, "execution_mode": mode}))
    if not candidates:
        return {"status": "unavailable", "reason_codes": ["NO_ELIGIBLE_PAIR"], "rejected_candidates": rejected}
    candidates.sort(key=lambda item: item[0])
    selected = {k: v for k, v in candidates[0][1].items() if k != "execution_mode"}
    return {"status": "ready", "selected": selected, "execution_mode": candidates[0][1]["execution_mode"],
            "evidence_basis": "provisional_policy", "policy_rule": requirement["id"],
            "explanation": f"초기 정책 '{requirement['id']}'의 요구를 충족하는 후보 중 불필요한 상향을 줄였습니다.",
            "reason_codes": ["TASK_REQUIREMENTS_MATCHED", "PROVISIONAL_POLICY", "CLOSEST_SUFFICIENT_PAIR"]
                            + (["PARTIAL_USER_OVERRIDE"] if model_override or effort_override else []),
            "capabilities_to_verify": [x for x in classification.get("required_capabilities", [])
                                       if x not in ("text", "image")],
            "candidates": [item[1] for item in candidates], "rejected_candidates": rejected}
