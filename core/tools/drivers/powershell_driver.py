#!/usr/bin/env python3
"""Non-executing PowerShell driver foundation."""

from typing import Any

from .base_driver import ProtocolDriver


class PowerShellDriver(ProtocolDriver):
    def __init__(self):
        super().__init__("powershell")

    def execute(
        self, script_cmd: str, timeout: int = 5, *, authorized: bool = False
    ) -> dict[str, Any]:
        del timeout
        return self.execute_request("localhost", script_cmd, authorized=authorized)
