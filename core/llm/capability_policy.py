"""Provider capabilities never grant or mutate tool permission modes."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


PERMISSION_MODES = {
    "OWNER_DIRECT",
    "OWNER_FULL_CONTROL",
    "OWNER_AUTONOMOUS",
    "ANSWER_ONLY",
    "WORKSPACE_READ",
    "WORKSPACE_WRITE",
    "LIVE_READ",
    "INFRASTRUCTURE_WRITE",
}


class CapabilityPolicyError(ValueError):
    pass


class CapabilityPolicy:
    @staticmethod
    def switch_provider(thread: dict[str, Any], provider_id: str) -> dict[str, Any]:
        if thread.get("permission_mode") not in PERMISSION_MODES:
            raise CapabilityPolicyError("Thread permission mode is invalid.")
        updated = deepcopy(thread)
        permission_mode = updated["permission_mode"]
        updated["provider_id"] = provider_id
        if updated["permission_mode"] != permission_mode:
            raise CapabilityPolicyError("Provider switching cannot alter permissions.")
        return updated

    @staticmethod
    def allowed_tools(profile: dict[str, Any], tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not profile["capabilities"]["tool_calling"]:
            return []
        return deepcopy(tools)
