#!/usr/bin/env python3
"""Protocol-driver registry with a disabled-by-default execution boundary."""

from typing import Any

from .base_driver import ProtocolDriver
from .powershell_driver import PowerShellDriver
from .rest_driver import RESTDriver
from .snmp_driver import SNMPDriver
from .sql_driver import SQLDriver
from .ssh_driver import SSHDriver
from .vmware_driver import VMwareDriver
from .winrm_driver import WinRMDriver


class DriverFactory:
    def __init__(self, *, execution_enabled: bool = False):
        self.execution_enabled = execution_enabled
        self.drivers = {
            "ssh": SSHDriver(),
            "rest": RESTDriver(),
            "powershell": PowerShellDriver(),
            "winrm": WinRMDriver(),
            "vmware": VMwareDriver(),
            "sql": SQLDriver(),
            "snmp": SNMPDriver(),
        }

    def get_driver(self, protocol: str) -> ProtocolDriver:
        if not isinstance(protocol, str):
            raise ValueError("Protocol must be a string.")
        normalized_protocol = protocol.casefold()
        if normalized_protocol not in self.drivers:
            raise ValueError(f"Unsupported protocol driver: {protocol}")
        return self.drivers[normalized_protocol]

    def plan_command(self, protocol: str, target: str, operation: str) -> dict[str, Any]:
        return self.get_driver(protocol).plan(target, operation)

    def execute_command(
        self,
        protocol: str,
        target: str,
        command: str,
        *,
        authorized: bool = False,
    ) -> dict[str, Any]:
        driver = self.get_driver(protocol)
        plan = driver.plan(target, command)
        if plan["status"] != "PLANNED":
            return plan
        if not self.execution_enabled:
            return {
                **plan,
                "status": "EXECUTION_DISABLED",
                "reason": "Protocol execution is disabled in the driver factory.",
            }
        return driver.execute_request(target, command, authorized=authorized)


if __name__ == "__main__":
    result = DriverFactory().execute_command("ssh", "example.invalid", "show status")
    print(result["status"])
