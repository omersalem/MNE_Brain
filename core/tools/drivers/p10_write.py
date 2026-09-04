"""P10 platform write adapters with no built-in network implementation."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

from core.tools.drivers.p10_live import P10LivePlatformDriver


class P10DriverError(RuntimeError):
    pass


class DisabledP10WriteDriver:
    """Default driver: validates the envelope and always remains disconnected."""

    live = False

    def execute(self, *, platform: str, target: str, commands: list[dict[str, Any]], timeout_seconds: int, binding_id: str = "") -> dict[str, Any]:
        del platform, target, commands, timeout_seconds, binding_id
        return {
            "status": "EXECUTION_DISABLED",
            "connection_attempted": False,
            "submitted": False,
            "output": None,
        }

    def abort(self, *, transaction_id: str) -> dict[str, Any]:
        del transaction_id
        return {"status": "NOT_APPLICABLE", "connection_attempted": False}


class SimulatedP10WriteDriver:
    """Injected deterministic test driver; it cannot open a connection."""

    live = False
    simulation = True

    def __init__(self, responses: list[dict[str, Any]] | None = None):
        self.responses = list(responses or [{"status": "SUBMITTED", "submitted": True}])
        self.calls: list[dict[str, Any]] = []
        self.abort_calls: list[str] = []

    def execute(self, *, platform: str, target: str, commands: list[dict[str, Any]], timeout_seconds: int, binding_id: str = "") -> dict[str, Any]:
        self.calls.append({
            "platform": platform,
            "target": target,
            "commands": deepcopy(commands),
            "timeout_seconds": timeout_seconds,
            "binding_id": binding_id,
        })
        result = self.responses.pop(0) if self.responses else {"status": "SUBMITTED", "submitted": True}
        return {"connection_attempted": False, "output": None, **deepcopy(result)}

    def abort(self, *, transaction_id: str) -> dict[str, Any]:
        self.abort_calls.append(transaction_id)
        return {"status": "ABORTED", "connection_attempted": False}


class InjectedPlatformWriteDriver:
    """Future live bridge: only an explicitly injected callback can submit."""

    def __init__(self, platform: str, callback: Callable[..., dict[str, Any]] | None = None):
        self.platform = platform
        self.callback = callback
        self.live = callback is not None

    def execute(self, *, platform: str, target: str, commands: list[dict[str, Any]], timeout_seconds: int, binding_id: str = "") -> dict[str, Any]:
        if platform != self.platform:
            raise P10DriverError("Platform adapter mismatch.")
        if self.callback is None:
            return {"status": "EXECUTION_DISABLED", "submitted": False, "connection_attempted": False, "output": None}
        return self.callback(target=target, commands=deepcopy(commands), timeout_seconds=timeout_seconds, binding_id=binding_id)

    def abort(self, *, transaction_id: str) -> dict[str, Any]:
        if self.callback is None or not hasattr(self.callback, "abort"):
            return {"status": "ABORT_UNAVAILABLE", "connection_attempted": False}
        return self.callback.abort(transaction_id=transaction_id)


class FortiGateWriteDriver(InjectedPlatformWriteDriver):
    def __init__(self, callback=None): super().__init__("fortinet_fortios", callback)


class F5BigIPWriteDriver(InjectedPlatformWriteDriver):
    def __init__(self, callback=None): super().__init__("f5_bigip", callback)


class FMCWriteDriver(InjectedPlatformWriteDriver):
    def __init__(self, callback=None): super().__init__("cisco_fmc", callback)


class TypedPowerShellWriteDriver(InjectedPlatformWriteDriver):
    def __init__(self, callback=None): super().__init__("windows_powershell", callback)


class VMwareWriteDriver(InjectedPlatformWriteDriver):
    def __init__(self, callback=None): super().__init__("vmware_vcenter", callback)


class CiscoSwitchWriteDriver(InjectedPlatformWriteDriver):
    def __init__(self, callback=None): super().__init__("cisco_switching", callback)


class FujitsuSwitchWriteDriver(InjectedPlatformWriteDriver):
    def __init__(self, callback=None): super().__init__("fujitsu_switching", callback)


class LinuxWriteDriver(InjectedPlatformWriteDriver):
    def __init__(self, callback=None): super().__init__("linux_host", callback)


PLATFORM_DRIVER_FAMILIES = {
    "fortinet_fortios": "FortiGate structured SSH transaction adapter",
    "f5_bigip": "BIG-IP transaction REST/tmsh adapter",
    "cisco_fmc": "FMC REST transaction adapter; managed FTD CLI writes prohibited",
    "windows_powershell": "Typed PowerShell/WinRM adapter",
    "vmware_vcenter": "vCenter API transaction adapter",
    "cisco_switching": "Cisco IOS structured configuration adapter",
    "fujitsu_switching": "Fujitsu structured configuration adapter",
    "linux_host": "Linux managed-operation adapter without arbitrary shell interpolation",
}


class P10PlatformDriverRegistry:
    """Route one typed transaction to one exact disabled-by-default adapter."""

    def __init__(self, callbacks: dict[str, Callable[..., dict[str, Any]]] | None = None, *, base_dir: Path | None = None, live: bool = False):
        callbacks = callbacks or {}
        if live:
            if callbacks:
                raise P10DriverError("Live registry does not accept injected callbacks.")
            root = Path(base_dir or Path(__file__).resolve().parents[3])
            self.adapters = {platform: P10LivePlatformDriver(root, platform=platform) for platform in PLATFORM_DRIVER_FAMILIES}
        else:
            self.adapters = {
                "fortinet_fortios": FortiGateWriteDriver(callbacks.get("fortinet_fortios")),
                "f5_bigip": F5BigIPWriteDriver(callbacks.get("f5_bigip")),
                "cisco_fmc": FMCWriteDriver(callbacks.get("cisco_fmc")),
                "windows_powershell": TypedPowerShellWriteDriver(callbacks.get("windows_powershell")),
                "vmware_vcenter": VMwareWriteDriver(callbacks.get("vmware_vcenter")),
                "cisco_switching": CiscoSwitchWriteDriver(callbacks.get("cisco_switching")),
                "fujitsu_switching": FujitsuSwitchWriteDriver(callbacks.get("fujitsu_switching")),
                "linux_host": LinuxWriteDriver(callbacks.get("linux_host")),
            }
        self.live = any(adapter.live for adapter in self.adapters.values())
        self._active_platform: str | None = None

    def execute(self, *, platform: str, target: str, commands: list[dict[str, Any]], timeout_seconds: int, binding_id: str = "") -> dict[str, Any]:
        adapter = self.adapters.get(platform)
        if adapter is None:
            raise P10DriverError("No P10 platform adapter is registered.")
        if not commands or any(item.get("transaction", {}).get("platform", platform) != platform for item in commands):
            raise P10DriverError("Platform transaction envelope mismatch.")
        self._active_platform = platform
        if isinstance(adapter, P10LivePlatformDriver):
            return adapter.execute(binding_id=binding_id, target=target, commands=commands, timeout_seconds=timeout_seconds)
        return adapter.execute(platform=platform, target=target, commands=commands, timeout_seconds=timeout_seconds, binding_id=binding_id)

    def readiness(self, *, platform: str, binding_id: str, target: str) -> dict[str, Any]:
        adapter = self.adapters.get(platform)
        if not isinstance(adapter, P10LivePlatformDriver):
            return {"status": "EXECUTION_DISABLED", "connection_attempted": False, "write_authorized": False}
        return adapter.readiness(binding_id=binding_id, target=target)

    def capture_state(self, *, platform: str, binding_id: str, target: str, commands: list[dict[str, Any]], timeout_seconds: int, postcheck: bool = False) -> dict[str, Any]:
        adapter = self.adapters.get(platform)
        if not isinstance(adapter, P10LivePlatformDriver):
            return {"status": "EXECUTION_DISABLED", "connection_attempted": False}
        return adapter.capture_state(binding_id=binding_id, target=target, commands=commands, timeout_seconds=timeout_seconds, postcheck=postcheck)

    def probe_write_authorization(self, *, platform: str, binding_id: str, target: str, timeout_seconds: int = 15) -> dict[str, Any]:
        adapter = self.adapters.get(platform)
        if not isinstance(adapter, P10LivePlatformDriver):
            return {"status": "EXECUTION_DISABLED", "connection_attempted": False, "write_authorized": False}
        return adapter.probe_write_authorization(binding_id=binding_id, target=target, timeout_seconds=timeout_seconds)

    def abort(self, *, transaction_id: str) -> dict[str, Any]:
        if self._active_platform is None:
            return {"status": "ABORT_UNAVAILABLE", "connection_attempted": False}
        return self.adapters[self._active_platform].abort(transaction_id=transaction_id)
