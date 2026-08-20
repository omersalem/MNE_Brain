#!/usr/bin/env python3
"""Non-connecting VMware driver foundation."""

from typing import Any

from .base_driver import ProtocolDriver


class VMwareDriver(ProtocolDriver):
    def __init__(self):
        super().__init__("vmware")

    def execute(
        self,
        vcenter_host: str,
        action: str,
        port: int = 443,
        timeout: int = 3,
        *,
        authorized: bool = False,
    ) -> dict[str, Any]:
        del port, timeout
        return self.execute_request(vcenter_host, action, authorized=authorized)
