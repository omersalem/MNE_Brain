"""P10 schema-governed operation catalog and strict transaction renderer."""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

import jsonschema
import yaml

from core.execution.p10_commands import P10CommandError, render_wire


class P10CatalogError(ValueError):
    """Raised when a P10 catalog or parameter contract fails closed."""


class P10OperationCatalog:
    """Load reviewed P10 templates and render typed, non-shell transactions."""

    _SAFE_STRING = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/@() +,-]{0,255}$")
    _DANGEROUS = re.compile(
        r"(?:[;&|`\r\n\x00]|\$\(|<\(|>\(|\b(?:invoke-expression|iex|cmd\.exe|"
        r"-encodedcommand|frombase64string|curl|wget|invoke-webrequest)\b)",
        re.IGNORECASE,
    )
    _SECRET_KEY = re.compile(r"(?:password|passwd|credential|token|secret|private[_-]?key|community)", re.IGNORECASE)

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent.parent
        schema = json.loads(
            (self.base_dir / "00_meta/schemas/p10-operation-catalog.schema.json").read_text(encoding="utf-8")
        )
        data = yaml.safe_load(
            (self.base_dir / "config/p10_operation_catalog.yaml").read_text(encoding="utf-8")
        ) or {}
        jsonschema.Draft7Validator(schema).validate(data)
        self.data = data
        self.transaction_schema = json.loads(
            (self.base_dir / "00_meta/schemas/p10-platform-transaction.schema.json").read_text(encoding="utf-8")
        )
        self._operations: dict[str, dict[str, Any]] = {}
        for family in data["families"]:
            for operation in family["operations"]:
                operation_id = operation["operation_id"]
                if operation_id in self._operations:
                    raise P10CatalogError(f"Duplicate P10 operation ID: {operation_id}")
                self._operations[operation_id] = {**deepcopy(operation), "family_id": family["family_id"]}

    def list_metadata(self) -> dict[str, Any]:
        operations = []
        for operation in self._operations.values():
            public = deepcopy(operation)
            public.pop("command_preview", None)
            public.pop("rollback_renderer", None)
            operations.append(public)
        return {
            "phase": "P10",
            "approval_state": "OWNER_CONTROLLED",
            "owner_reference": "MNE-BRAIN-OWNER",
            "audit_mode": "IN_MEMORY_ONLY",
            "retention": "NONE",
            "family_count": len(self.data["families"]),
            "template_count": len(self._operations),
            "action_variant_count": sum(len(item["action_variants"]) for item in self._operations.values()),
            "operations": operations,
            "live_execution_enabled": False,
        }

    def get(self, operation_id: str) -> dict[str, Any]:
        operation = self._operations.get(operation_id)
        if not operation:
            raise P10CatalogError(f"Unlisted operation: {operation_id}")
        if operation["template_status"] != "reviewed":
            raise P10CatalogError("Operation template is not reviewed.")
        return deepcopy(operation)

    def validate_parameters(self, operation: dict[str, Any], parameters: Any) -> dict[str, Any]:
        if not isinstance(parameters, dict):
            raise P10CatalogError("Operation parameters must be an object.")
        try:
            jsonschema.Draft7Validator(operation["parameter_schema"]).validate(parameters)
        except jsonschema.ValidationError as exc:
            raise P10CatalogError(f"Parameter validation failed: {exc.message}") from exc
        if parameters.get("action") not in operation["action_variants"]:
            raise P10CatalogError("The requested action variant is outside this reviewed template.")
        self._validate_values(parameters)
        return deepcopy(parameters)

    def _validate_values(self, value: Any, path: str = "parameters") -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if self._SECRET_KEY.search(key):
                    raise P10CatalogError(f"Secret-bearing parameter is prohibited: {path}.{key}")
                self._validate_values(item, f"{path}.{key}")
            return
        if isinstance(value, list):
            for index, item in enumerate(value):
                self._validate_values(item, f"{path}[{index}]")
            return
        if isinstance(value, str):
            if len(value) > 256 or not self._SAFE_STRING.fullmatch(value) or self._DANGEROUS.search(value):
                raise P10CatalogError(f"Unsafe string value rejected at {path}.")
        elif value is not None and not isinstance(value, (bool, int)):
            raise P10CatalogError(f"Unsupported parameter type at {path}.")

    @staticmethod
    def _canonical(value: Any) -> str:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def render(
        self,
        operation: dict[str, Any],
        parameters: dict[str, Any],
        *,
        target: str,
        rollback: bool = False,
    ) -> dict[str, Any]:
        """Build one exact structured platform transaction; never invoke a shell."""
        validated = self.validate_parameters(operation, parameters)
        renderer = operation["rollback_renderer"] if rollback else operation["command_renderer"]
        transaction = {
            "transaction_version": "1.0",
            "platform": operation["platform"],
            "operation_id": operation["operation_id"],
            "operation_type": operation["operation_type"],
            "renderer": renderer,
            "target": target,
            "action": validated["action"],
            "arguments": {key: value for key, value in validated.items() if key != "action"},
            "transaction_mode": operation["transaction_mode"],
            "rollback": rollback,
        }
        jsonschema.Draft7Validator(self.transaction_schema).validate(transaction)
        try:
            wire = render_wire(transaction)
        except P10CommandError as exc:
            raise P10CatalogError(str(exc)) from exc
        display_commands = list(wire["display"])
        display = self._canonical(display_commands)
        return {
            "commands": [{"sequence": 1, "display": display_commands[0], "transaction": transaction, "wire": wire}],
            "display_commands": display_commands,
            "bundle_hash": hashlib.sha256(display.encode("utf-8")).hexdigest(),
            "contains_credentials": False,
            "hidden_chaining": False,
        }


def common_parameter_schema(*, extra_required: list[str] | None = None) -> dict[str, Any]:
    """Return the strict common parameter contract used by catalog generation tests."""
    required = ["action", "resource_name", *(extra_required or [])]
    return {
        "type": "object",
        "additionalProperties": False,
        "required": required,
        "properties": {
            "action": {"type": "string", "pattern": "^[a-z][a-z0-9_]{1,63}$"},
            "resource_name": {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:/@() +,-]{0,127}$"},
            "value": {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:/@() +,-]{0,255}$"},
            "secondary_value": {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:/@() +,-]{0,255}$"},
            "interface": {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,63}$"},
            "position": {"type": "integer", "minimum": 1, "maximum": 100000},
            "size_gb": {"type": "integer", "minimum": 1, "maximum": 65536},
            "enabled": {"type": "boolean"},
            "force": {"type": "boolean"},
        },
    }
