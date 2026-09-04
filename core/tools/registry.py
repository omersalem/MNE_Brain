"""Central P11 tool inventory; models can propose only declared names."""

from __future__ import annotations

from copy import deepcopy


TOOL_DEFINITIONS = {
    "workspace.list": {"permission": "WORKSPACE_READ", "mutating": False},
    "workspace.search": {"permission": "WORKSPACE_READ", "mutating": False},
    "workspace.read": {"permission": "WORKSPACE_READ", "mutating": False},
    "workspace.status": {"permission": "WORKSPACE_READ", "mutating": False},
    "workspace.diff": {"permission": "WORKSPACE_READ", "mutating": False},
    "workspace.prepare_patch": {"permission": "WORKSPACE_WRITE", "mutating": False},
    "workspace.apply_approved_patch": {"permission": "WORKSPACE_WRITE", "mutating": True},
    "workspace.run_validator": {"permission": "WORKSPACE_WRITE", "mutating": False},
    "workspace.prepare_rollback": {"permission": "WORKSPACE_WRITE", "mutating": False},
    "workspace.apply_approved_rollback": {"permission": "WORKSPACE_WRITE", "mutating": True},
    "mne.build_evidence": {"permission": "WORKSPACE_READ", "mutating": False},
    "mne.plan_investigation": {"permission": "WORKSPACE_READ", "mutating": False},
    "mne.prepare_live_read": {"permission": "LIVE_READ", "mutating": False},
    "mne.execute_approved_live_read": {"permission": "LIVE_READ", "mutating": True},
    "owner_direct.discover": {"permission": "OWNER_DIRECT", "mutating": False},
    "owner_direct.prepare_write": {"permission": "OWNER_DIRECT", "mutating": False},
    "owner_direct.identity_audit": {"permission": "OWNER_DIRECT", "mutating": False},
    "p10.prepare": {"permission": "INFRASTRUCTURE_WRITE", "mutating": False},
    "p10.prepare_critical": {"permission": "INFRASTRUCTURE_WRITE", "mutating": False},
    "p10.approve": {"permission": "INFRASTRUCTURE_WRITE", "mutating": False},
    "p10.execute": {"permission": "INFRASTRUCTURE_WRITE", "mutating": True},
    "p10.rollback_prepare": {"permission": "INFRASTRUCTURE_WRITE", "mutating": False},
}

_STRING = {"type": "string", "minLength": 1}
TOOL_INPUT_SCHEMAS = {
    "workspace.list": {"type": "object", "properties": {"path": _STRING}, "additionalProperties": False},
    "workspace.search": {"type": "object", "required": ["query"], "properties": {"query": _STRING, "path": _STRING}, "additionalProperties": False},
    "workspace.read": {"type": "object", "required": ["path"], "properties": {"path": _STRING, "max_bytes": {"type": "integer", "minimum": 1, "maximum": 1000000}}, "additionalProperties": False},
    "workspace.status": {"type": "object", "properties": {}, "additionalProperties": False},
    "workspace.diff": {"type": "object", "properties": {}, "additionalProperties": False},
    "workspace.prepare_patch": {"type": "object", "required": ["unified_diff"], "properties": {"unified_diff": _STRING}, "additionalProperties": False},
    "workspace.run_validator": {"type": "object", "required": ["validator_id"], "properties": {"validator_id": _STRING, "extra_args": {"type": "array", "items": {"type": "string"}}, "timeout_seconds": {"type": "integer", "minimum": 1, "maximum": 1800}}, "additionalProperties": False},
    "workspace.prepare_rollback": {"type": "object", "required": ["plan_id"], "properties": {"plan_id": _STRING}, "additionalProperties": False},
    "mne.build_evidence": {"type": "object", "required": ["question"], "properties": {"question": _STRING, "target_entities": {"type": "array", "items": _STRING}, "supplemental_evidence": {"type": "array", "items": {"type": "object"}}}, "additionalProperties": False},
    "mne.plan_investigation": {"type": "object", "required": ["question"], "properties": {"question": _STRING}, "additionalProperties": False},
    "mne.prepare_live_read": {"type": "object", "required": ["binding_id", "target", "check_id"], "properties": {"binding_id": _STRING, "target": _STRING, "check_id": _STRING}, "additionalProperties": False},
    "owner_direct.discover": {"type": "object", "required": ["entity_id", "protocol", "operation"], "properties": {"entity_id": _STRING, "protocol": _STRING, "operation": _STRING, "target": _STRING, "owner_supplied_target": {"type": "boolean"}, "trusted_identity": _STRING}, "additionalProperties": False},
    "owner_direct.prepare_write": {"type": "object", "required": ["entity_id", "protocol", "operations", "intended_change", "expected_impact", "downtime_risk", "blast_radius", "prechecks", "postchecks", "owner_requested"], "properties": {"entity_id": _STRING, "protocol": _STRING, "operations": {"type": "array", "items": _STRING}, "intended_change": _STRING, "expected_impact": _STRING, "downtime_risk": _STRING, "blast_radius": _STRING, "prechecks": {"type": "array", "items": _STRING}, "postchecks": {"type": "array", "items": _STRING}, "rollback_steps": {"type": "array", "items": _STRING}, "trusted_identity": _STRING, "observed_identity": _STRING, "target": _STRING, "owner_supplied_target": {"type": "boolean"}, "owner_requested": {"const": True}}, "additionalProperties": False},
    "owner_direct.identity_audit": {"type": "object", "required": ["requests"], "properties": {"requests": {"type": "array", "items": {"type": "object"}}}, "additionalProperties": False},
    "p10.prepare": {"type": "object", "required": ["operation_id", "binding_id", "target", "identity_pin", "parameters", "evidence"], "properties": {"operation_id": _STRING, "binding_id": _STRING, "target": _STRING, "identity_pin": _STRING, "parameters": {"type": "object"}, "evidence": {"type": "object"}}, "additionalProperties": False},
    "p10.prepare_critical": {"type": "object", "required": ["platform", "protocol", "binding_id", "target", "identity_pin", "commands", "rollback_commands", "evidence", "warning", "irreversible"], "properties": {"platform": _STRING, "protocol": {"enum": ["ssh_cli", "winrm_powershell", "fmc_rest", "vcenter_rest"]}, "binding_id": _STRING, "target": _STRING, "identity_pin": _STRING, "commands": {"type": "array", "items": _STRING}, "rollback_commands": {"type": "array", "items": _STRING}, "evidence": {"type": "object"}, "warning": {"type": "object"}, "irreversible": {"type": "boolean"}}, "additionalProperties": False},
}


class ToolRegistry:
    def list(self) -> list[dict[str, object]]:
        return [{"tool_name": name, **deepcopy(spec)} for name, spec in sorted(TOOL_DEFINITIONS.items())]

    def get(self, tool_name: str) -> dict[str, object]:
        if tool_name not in TOOL_DEFINITIONS:
            raise ValueError("Unknown tool name.")
        return deepcopy(TOOL_DEFINITIONS[tool_name])

    def provider_tools(self, allowed_names: set[str] | frozenset[str]) -> list[dict[str, object]]:
        """Return provider-neutral proposal schemas; the broker remains authoritative."""
        return [
            {
                "name": name,
                "description": f"Propose the governed {name} operation. Execution is separate and permission-gated.",
                "input_schema": deepcopy(TOOL_INPUT_SCHEMAS[name]),
                "strict": True,
            }
            for name in sorted(allowed_names)
            if name in TOOL_DEFINITIONS and name in TOOL_INPUT_SCHEMAS
        ]
