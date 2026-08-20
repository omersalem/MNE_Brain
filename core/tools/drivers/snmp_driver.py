#!/usr/bin/env python3
"""Non-connecting SNMP driver foundation."""

from typing import Any

from .base_driver import ProtocolDriver


class SNMPDriver(ProtocolDriver):
    def __init__(self):
        super().__init__("snmp")

    def execute(
        self,
        target_ip: str,
        oid: str,
        port: int = 161,
        timeout: int = 3,
        *,
        authorized: bool = False,
    ) -> dict[str, Any]:
        del port, timeout
        return self.execute_request(target_ip, oid, authorized=authorized)
