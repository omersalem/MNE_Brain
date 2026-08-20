#!/usr/bin/env python3
"""Non-connecting WinRM driver foundation."""

from typing import Any

from .base_driver import ProtocolDriver


class WinRMDriver(ProtocolDriver):
    def __init__(self):
        super().__init__("winrm")

    def execute(
        self,
        host: str,
        command: str,
        port: int = 5985,
        timeout: int = 3,
        *,
        authorized: bool = False,
    ) -> dict[str, Any]:
        del port, timeout
        return self.execute_request(host, command, authorized=authorized)
