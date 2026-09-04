"""Fail-closed tool permission modes independent from provider selection."""

from __future__ import annotations

from pathlib import Path

import yaml


class ToolPermissionError(PermissionError):
    pass


class ToolPermissions:
    def __init__(self, base_dir: Path):
        policy = yaml.safe_load((base_dir / "config/p11_tool_policy.yaml").read_text(encoding="utf-8")) or {}
        self.modes = {name: frozenset(tools) for name, tools in policy.get("permission_modes", {}).items()}
        required = {"OWNER_DIRECT", "OWNER_FULL_CONTROL", "OWNER_AUTONOMOUS", "ANSWER_ONLY", "WORKSPACE_READ", "WORKSPACE_WRITE", "LIVE_READ", "INFRASTRUCTURE_WRITE"}
        if set(self.modes) != required:
            raise ToolPermissionError("P11 permission modes are incomplete.")

    def require(self, permission_mode: str, tool_name: str) -> None:
        if tool_name not in self.modes.get(permission_mode, frozenset()):
            raise ToolPermissionError(f"Tool {tool_name} is not allowed in {permission_mode}.")
