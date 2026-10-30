"""Separate safe configuration parsing from scoped security readiness."""
from __future__ import annotations

import hashlib
from pathlib import Path
import re

from .core import inside, matches, validate_patterns

AREAS = ("authorization", "inputs-files", "external-tools", "dependencies",
         "secrets-logging", "browser", "execution", "abuse")


def described(value) -> bool:
    return (isinstance(value, str) and bool(value.strip()) and
            not re.fullmatch(r"(?i)(?:todo|tbd|pending|draft|작성 필요|미정|미작성|<[^>]*>)", value.strip()))


def validate(root: Path, project: dict) -> dict | None:
    """Reject malformed/unsafe config; report unfinished review without a global lock."""
    pending, ready_controls = [], []
    review = {"state": "pending", "pending": pending, "controls": ready_controls,
              "document": None, "document_sha256": None}
    project["security_review"] = review

    def wait(reason, area="design", paths=None, checks=None):
        pending.append({"area": area, "reason": reason, "paths": paths or ["**"], "checks": checks or []})

    security = project.get("security")
    if security is None:
        wait("security_design_missing")
        return None
    if not isinstance(security, dict) or set(security) - {
            "state", "document", "document_sha256", "assets", "trust_boundaries", "controls"}:
        raise ValueError("invalid security design fields")
    state = security.get("state", "draft")
    if state not in ("draft", "reviewed"):
        raise ValueError("security.state must be draft or reviewed")
    relative = security.get("document", "")
    if not isinstance(relative, str):
        raise ValueError("security.document must be a repository-relative Markdown path")
    text = ""
    if relative:
        path = inside(root, relative)
        if path.suffix != ".md" or (path.exists() and not path.is_file()):
            raise ValueError("security.document must reference Markdown")
        review["document"] = relative
        try:
            with path.open("rb") as stream:
                content = stream.read(2 * 1024 * 1024 + 1)
            if len(content) > 2 * 1024 * 1024:
                wait("security_document_size_limit")
            else:
                review["document_sha256"] = hashlib.sha256(content).hexdigest()
                text = content.decode("utf-8")
        except (OSError, UnicodeError):
            wait("security_document_unavailable")
    else:
        wait("security_document_missing")
    if state != "reviewed":
        wait("security_design_draft")
    if not text.strip() or re.search(r"작성 필요|(?im:^\s*(?:상태|status):\s*draft\b)", text):
        wait("security_document_unfilled")
    if not review["document_sha256"] or security.get("document_sha256") != review["document_sha256"]:
        wait("security_document_review_outdated")
    for field in ("assets", "trust_boundaries"):
        values = security.get(field, [])
        if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
            raise ValueError(f"invalid security.{field}")
        if not values or not all(described(v) for v in values):
            wait(f"security_{field}_unfinished")
    controls = security.get("controls", [])
    if not isinstance(controls, list):
        raise ValueError("security.controls must be an array")
    observed = set()
    checks = {c["id"]: c for c in project.get("checks", [])}
    for control in controls:
        if not isinstance(control, dict) or set(control) - {"area", "status", "description", "paths", "checks"}:
            raise ValueError("invalid security control fields")
        area, status = control.get("area"), control.get("status")
        if not isinstance(area, str) or area not in AREAS or area in observed:
            raise ValueError("security controls need unique supported areas")
        observed.add(area)
        if status not in ("required", "not_applicable", "pending"):
            raise ValueError(f"invalid security control status: {area}")
        paths = control.get("paths", [])
        if paths:
            validate_patterns(paths, f"security control {area} paths")
        elif not isinstance(paths, list):
            raise ValueError(f"invalid security control paths: {area}")
        names = control.get("checks", [])
        if not isinstance(names, list) or not all(isinstance(n, str) for n in names) or len(set(names)) != len(names):
            raise ValueError(f"invalid security check references: {area}")
        if status == "not_applicable":
            if names or paths:
                raise ValueError(f"not_applicable control must explain exclusion without executable coverage: {area}")
            if not described(control.get("description")):
                wait("security_exclusion_needs_reason", area)
            continue
        if status == "pending":
            wait("security_control_review_pending", area, paths, names)
            continue
        valid = bool(paths and names and described(control.get("description")))
        for name in names:
            check = checks.get(name)
            valid = valid and bool(check and name != "doctor" and check.get("covers_behavior", True)
                                   and not check.get("allow_flaky", False)
                                   and check.get("test_summary") in ("unittest", "junit"))
        if valid:
            ready_controls.append({"area": area, "paths": paths, "checks": names})
        else:
            wait("security_control_needs_requirement_and_strict_tests", area, paths, names)
    for area in AREAS:
        if area not in observed:
            wait("security_area_not_assessed", area)
    review["state"] = "pending" if pending else "ready"
    return security


def for_scope(review: dict | None, paths: list[str], *, full=False, workflow=None, impact_checks=()) -> dict:
    if review is None:
        return {"state": "not_configured", "applicable_pending": [], "project_pending": []}
    pending = review["pending"]
    entire = full or workflow in paths or review.get("document") in paths
    applicable = [item for item in pending if entire or any(matches(p, item["paths"]) for p in paths)
                  or bool(set(item.get("checks", [])) & set(impact_checks))]
    return {"state": "pending" if applicable else "ready", "scope": "project" if full else "selected_paths",
            "applicable_pending": applicable, "project_pending": pending,
            "document": review.get("document"), "document_sha256": review.get("document_sha256")}
