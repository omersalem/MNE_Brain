#!/usr/bin/env python3
"""Non-connecting SSH driver foundation."""

from typing import Any

from .base_driver import ProtocolDriver


class SSHDriver(ProtocolDriver):
    def __init__(self):
        super().__init__("ssh")

    def execute(
        self,
        host: str,
        command: str,
        port: int = 22,
        timeout: int = 3,
        *,
        authorized: bool = False,
    ) -> dict[str, Any]:
        del port, timeout
        return self.execute_request(host, command, authorized=authorized)
