"""Provider-neutral stdio MCP relay for MNE Brain governed tools.

The child process has no MNE credentials and cannot execute tools itself.  It
forwards only the reviewed allowlist to a one-turn loopback capability owned by
the authenticated MNE Brain server process.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.tools.registry import TOOL_INPUT_SCHEMAS


ALIASES = {
    "workspace_list": "workspace.list",
    "workspace_search": "workspace.search",
    "workspace_read": "workspace.read",
    "workspace_status": "workspace.status",
    "workspace_diff": "workspace.diff",
    "mne_build_evidence": "mne.build_evidence",
    "mne_plan_investigation": "mne.plan_investigation",
    "mne_prepare_live_read": "mne.prepare_live_read",
    "owner_direct_discover": "owner_direct.discover",
    "owner_direct_prepare_write": "owner_direct.prepare_write",
    "owner_direct_identity_audit": "owner_direct.identity_audit",
    "p10_prepare": "p10.prepare",
    "p10_prepare_critical": "p10.prepare_critical",
}

DESCRIPTIONS = {
    "workspace.list": "List a bounded path inside the governed MNE Brain workspace.",
    "workspace.search": "Search bounded, non-secret workspace text through MNE Brain.",
    "workspace.read": "Read a bounded, non-secret workspace file through MNE Brain.",
    "workspace.status": "Read the current governed workspace status.",
    "workspace.diff": "Read the current governed workspace diff without changing files.",
    "mne.build_evidence": "Build a bounded MNE evidence pack from workspace knowledge.",
    "mne.plan_investigation": "Create a deterministic evidence-driven investigation plan.",
    "mne.prepare_live_read": "Run one exact owner-governed P7 read for a pinned binding, target, and check.",
    "owner_direct.discover": "Run one exact Owner Direct read and return sanitized identity evidence without updating pins.",
    "owner_direct.prepare_write": "Prepare one exact Owner Direct risk warning. This never sends a write.",
    "owner_direct.identity_audit": "Run one requested identity attempt per exact canonical asset without changing canonical records.",
    "p10.prepare": "Prepare, but never approve or execute, one exact cataloged P10 change package.",
    "p10.prepare_critical": "Prepare, but never approve or execute, one critical P10 change package.",
}

TOOLS = [
    {
        "name": alias,
        "description": DESCRIPTIONS[tool_name],
        "inputSchema": TOOL_INPUT_SCHEMAS[tool_name],
    }
    for alias, tool_name in ALIASES.items()
]


def _reply(request_id: Any, *, result: dict[str, Any] | None = None, error: dict[str, Any] | None = None) -> None:
    payload = {"jsonrpc": "2.0", "id": request_id}
    payload["error" if error is not None else "result"] = error if error is not None else (result or {})
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def _call_parent(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    url = os.environ.get("MNE_OPENCODE_MCP_URL", "")
    token = os.environ.get("MNE_OPENCODE_MCP_TOKEN", "")
    if not url.startswith("http://127.0.0.1:") or not token:
        raise RuntimeError("Governed MNE tool capability is unavailable.")
    body = json.dumps({"name": name, "arguments": arguments}, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + token},
    )
    try:
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request, timeout=180) as response:
            value = json.loads(response.read(2_000_000).decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        raise RuntimeError("Governed MNE tool call failed safely.") from exc
    if not isinstance(value, dict):
        raise RuntimeError("Governed MNE tool returned an invalid envelope.")
    return value


def main() -> int:
    allowed = set(ALIASES)
    for raw in sys.stdin:
        try:
            message = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(message, dict) or message.get("jsonrpc") != "2.0" or "id" not in message:
            continue
        request_id = message["id"]
        method = message.get("method")
        params = message.get("params") if isinstance(message.get("params"), dict) else {}
        try:
            if method == "initialize":
                _reply(
                    request_id,
                    result={
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {"listChanged": False}},
                        "serverInfo": {"name": "mne-governed-tools", "version": "2.0"},
                    },
                )
            elif method == "ping":
                _reply(request_id, result={})
            elif method == "tools/list":
                _reply(request_id, result={"tools": TOOLS})
            elif method == "tools/call":
                name = str(params.get("name", ""))
                arguments = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
                if name not in allowed:
                    raise RuntimeError("Tool is outside the governed MNE allowlist.")
                value = _call_parent(name, arguments)
                _reply(
                    request_id,
                    result={
                        "content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False, sort_keys=True)}],
                        "isError": value.get("status") == "FAILED",
                    },
                )
            else:
                _reply(request_id, error={"code": -32601, "message": "Method not found"})
        except Exception as exc:
            _reply(
                request_id,
                result={"content": [{"type": "text", "text": str(exc)[:500]}], "isError": True},
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
