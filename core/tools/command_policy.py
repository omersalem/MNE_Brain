"""Exact argv validators with no shell expansion."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

import yaml


class CommandPolicyError(ValueError):
    pass


class CommandPolicy:
    _ARG = re.compile(r"^[A-Za-z0-9_./\\:=,+-]{1,240}$")

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir.resolve()
        policy = yaml.safe_load((self.base_dir / "config/p11_tool_policy.yaml").read_text(encoding="utf-8")) or {}
        self.validators = policy.get("validators", {})

    def run(self, validator_id: str, extra_args: list[str] | None = None, *, timeout_seconds: int = 300) -> dict[str, Any]:
        argv = self.validators.get(validator_id)
        if not isinstance(argv, list) or not argv:
            raise CommandPolicyError("Validator is not allowlisted.")
        extras = extra_args or []
        if any(not isinstance(arg, str) or not self._ARG.fullmatch(arg) or arg.lower() in {"-c", "/c", "-encodedcommand"} for arg in extras):
            raise CommandPolicyError("Validator argument rejected.")
        completed = subprocess.run([*argv, *extras], cwd=self.base_dir, shell=False, capture_output=True, text=True, timeout=max(1, min(timeout_seconds, 600)), check=False)
        return {"validator_id": validator_id, "returncode": completed.returncode, "stdout": completed.stdout[-20000:], "stderr": completed.stderr[-20000:], "status": "PASSED" if completed.returncode == 0 else "FAILED"}

