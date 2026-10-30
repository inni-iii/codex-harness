"""Bounded HTTP MCP reachability probe; no tools/call, models or raw errors."""
from __future__ import annotations

import json
import re
import time
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .core import strict_json

MAX_RESPONSE = 2_000_000
PROTOCOL = "2025-03-26"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("redirect_not_allowed")


def urlopen(request, timeout):
    return build_opener(NoRedirect()).open(request, timeout=timeout)


def _message(text: str) -> dict:
    value = strict_json(text)
    if not isinstance(value, dict) or value.get("jsonrpc") != "2.0":
        raise ValueError("invalid_rpc_message")
    return value


def decode(text: str) -> dict:
    if text.lstrip().startswith("{"):
        return _message(text)
    data = "\n".join(line[5:].lstrip(" ") for line in text.splitlines() if line.startswith("data:"))
    if data:
        return _message(data)
    raise ValueError("missing_rpc_message")


def _result(value: dict, request_id: int):
    # Server notifications may precede the response; they never become actions.
    if "method" in value:
        if "id" in value:
            raise ValueError("server_request_unsupported")
        return None
    if (type(value.get("id")) is not int or value["id"] != request_id
            or "error" in value or not isinstance(value.get("result"), dict)):
        raise ValueError("invalid_or_failed_rpc_response")
    return value


def _response(response, request_id, timeout):
    mime = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
    if request_id is not None and mime not in {"application/json", "text/event-stream"}:
        raise ValueError("unexpected_content_type")
    deadline = time.monotonic() + timeout
    content = bytearray()
    size = 0
    while True:
        if time.monotonic() >= deadline:
            raise ValueError("response_deadline")
        chunk = response.read1(min(65536, MAX_RESPONSE - size + 1))
        if not chunk:
            break
        size += len(chunk)
        if size > MAX_RESPONSE:
            raise ValueError("response_size_limit")
        content.extend(chunk)
        if request_id is None:
            raise ValueError("notification_response_must_be_empty")
        if mime == "text/event-stream":
            content[:] = content.replace(b"\r\n", b"\n")
            while b"\n\n" in content:
                event, _, remainder = content.partition(b"\n\n")
                content[:] = remainder
                if not any(line.startswith(b"data:") for line in event.splitlines()):
                    continue
                result = _result(decode(event.decode("utf-8")), request_id)
                if result is not None:
                    return result
    if request_id is None:
        return {}
    if mime == "text/event-stream":
        raise ValueError("stream_ended_without_response")
    result = _result(decode(content.decode("utf-8")), request_id)
    if result is None:
        raise ValueError("missing_rpc_response")
    return result


def probe(url: str, timeout: float = 10) -> dict:
    headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}

    def post(payload):
        request = Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
        with urlopen(request, timeout=timeout) as response:
            session = response.headers.get("Mcp-Session-Id")
            if session:
                if (not re.fullmatch(r"[\x21-\x7e]{1,256}", session)
                        or headers.get("Mcp-Session-Id", session) != session):
                    raise ValueError("invalid_or_changed_session")
                headers["Mcp-Session-Id"] = session
            if "id" not in payload and getattr(response, "status", None) != 202:
                raise ValueError("notification_not_accepted")
            return _response(response, payload.get("id"), timeout)

    try:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
            raise ValueError("explicit_https_endpoint_required")
        if not 0 < timeout <= 60:
            raise ValueError("invalid_timeout")
        initial = post({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": PROTOCOL, "capabilities": {},
            "clientInfo": {"name": "repository-harness-check", "version": "1.0"}}})
        if initial["result"].get("protocolVersion") != PROTOCOL:
            raise ValueError("unsupported_protocol")
        headers["MCP-Protocol-Version"] = PROTOCOL
        post({"jsonrpc": "2.0", "method": "notifications/initialized"})
        result = post({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})["result"]
        tools = result.get("tools")
        if not isinstance(tools, list) or not tools or len(tools) > 2000:
            raise ValueError("invalid_tool_list")
        names = [t.get("name") if isinstance(t, dict) else None for t in tools]
        if (any(not isinstance(n, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", n) for n in names)
                or len(set(names)) != len(names)):
            raise ValueError("invalid_tool_names")
        return {"status": "passed", "tool_count": len(names), "tool_names": names,
                "scope": "first_tools_page", "more_tools": bool(result.get("nextCursor")), "protocol": PROTOCOL}
    except (OSError, ValueError, KeyError, TypeError, AttributeError, RecursionError):
        return {"status": "unavailable", "error": "connection_or_response_validation_failed"}
