"""Normalize catalogs without assuming model entitlement."""

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess


class CatalogError(ValueError):
    pass


@dataclass(frozen=True)
class Model:
    id: str
    efforts: tuple[str, ...]
    default_effort: str | None
    hidden: bool
    modalities: tuple[str, ...]
    priority: int


@dataclass(frozen=True)
class Catalog:
    models: tuple[Model, ...]
    source: str

    def find(self, name: str) -> Model | None:
        return next((m for m in self.models if m.id == name), None)


def parse_catalog(payload: object, source: str = "provided") -> Catalog:
    if not isinstance(payload, dict):
        raise CatalogError("모델 목록은 JSON 객체여야 합니다.")
    body = payload.get("result", payload)
    if not isinstance(body, dict):
        raise CatalogError("모델 목록의 result 형식이 잘못되었습니다.")
    if body.get("nextCursor"):
        raise CatalogError("모든 페이지를 가져오지 않은 모델 목록입니다.")
    entries = body.get("models", body.get("data"))
    if not isinstance(entries, list) or not entries:
        raise CatalogError("모델 목록이 비어 있거나 형식이 잘못되었습니다.")
    models: list[Model] = []
    for position, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise CatalogError("모델 항목은 객체여야 합니다.")
        name = entry.get("slug", entry.get("model", entry.get("id")))
        levels = entry.get("supported_reasoning_levels", entry.get("supportedReasoningEfforts"))
        if not isinstance(name, str) or not name or not isinstance(levels, list):
            raise CatalogError("모델 식별자 또는 지원 effort가 누락되었습니다.")
        efforts = []
        for level in levels:
            effort = level if isinstance(level, str) else (
                level.get("effort", level.get("reasoningEffort")) if isinstance(level, dict) else None
            )
            if not isinstance(effort, str) or not effort:
                raise CatalogError("지원 effort 항목이 잘못되었습니다.")
            efforts.append(effort)
        if not efforts or any(m.id == name for m in models):
            raise CatalogError("지원 effort가 비어 있거나 모델 식별자가 중복됩니다.")
        default = entry.get("default_reasoning_level", entry.get("defaultReasoningEffort"))
        if default is not None and default not in efforts:
            raise CatalogError("기본 effort가 지원 목록에 없습니다.")
        modalities = entry.get("input_modalities", entry.get("inputModalities", []))
        if not isinstance(modalities, list) or not all(isinstance(x, str) for x in modalities):
            raise CatalogError("입력 형식 목록이 잘못되었습니다.")
        priority = entry.get("priority", position)
        if type(priority) is not int:
            raise CatalogError("모델 우선순위 형식이 잘못되었습니다.")
        models.append(Model(name, tuple(dict.fromkeys(efforts)), default,
                            entry.get("visibility") == "hide" or entry.get("hidden") is True,
                            tuple(modalities), priority))
    return Catalog(tuple(models), source)


def load_catalog(path: Path | None, executable: str, timeout: float) -> Catalog:
    try:
        if path is not None:
            return parse_catalog(json.loads(path.read_text(encoding="utf-8")), "provided")
        result = subprocess.run([executable, "debug", "models"], capture_output=True,
                                text=True, timeout=timeout, check=False)
        if result.returncode:
            raise CatalogError("Codex 모델 목록 조회에 실패했습니다.")
        # Successful exit does not prove server freshness: the CLI may have used its cache.
        return parse_catalog(json.loads(result.stdout), "cli_resolved")
    except (OSError, UnicodeError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        raise CatalogError("모델 목록을 읽거나 조회할 수 없습니다.") from exc


def describe(catalog: Catalog, effort_policy: dict) -> dict:
    return {
        "source": catalog.source,
        "entitlement_verified": False,
        "models": [
            {"model": m.id, "default_effort": m.default_effort, "hidden": m.hidden,
             "input_modalities": list(m.modalities), "catalog_priority": m.priority,
             "pairs": [{"model": m.id, "effort": effort,
                        "execution_mode": ("delegated" if effort in effort_policy["delegating"] else
                                           "single_agent" if effort in effort_policy["single_agent"] else "unknown")}
                       for effort in m.efforts]}
            for m in catalog.models
        ],
    }
