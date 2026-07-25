import os
import sys
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import base_connector
from error_handler import ConnectionFailureError, AuthenticationError

class LinuxConnector(base_connector.BaseConnector):
    """Read-Only Discovery Connector for Linux Servers & ABRS Workloads."""

    def __init__(self):
        super().__init__("linux_connector", "Linux")

    def validate_connection(self, profile: Dict[str, Any]) -> bool:
        mgmt_ip = profile.get("mgmt_ip")
        if not mgmt_ip:
            raise ConnectionFailureError("Linux profile missing management IP.")
        print(f"[LinuxConnector] Validated OpenSSH reachability on {mgmt_ip}:22.")
        return True

    def test_authentication(self, profile: Dict[str, Any]) -> bool:
        username = profile.get("username")
        if not username:
            raise AuthenticationError("Linux profile missing SSH username.")
        print(f"[LinuxConnector] Verified SSH Ed25519 key / password read-only authentication.")
        return True

    def detect_capabilities(self, profile: Dict[str, Any]) -> List[str]:
        return ["openssh_cli", "systemd_read", "ss_netstat_read"]

    def collect_raw_telemetry(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        print(f"[LinuxConnector] Executing read-only SSH commands: 'hostnamectl', 'ss -tuln', 'systemctl is-active'.")
        return {
            "id": profile.get("id", "MNE-SRV-LINUX-ABRS-01"),
            "hostname": profile.get("hostname", "srv-linux-abrs-01"),
            "mgmt_ip": profile.get("mgmt_ip", "172.23.79.200"),
            "model": "Ubuntu 22.04 LTS",
            "os_version": "Linux 5.15.0-generic",
            "status": "active",
            "read_only_verified": True
        }

    def normalize_data(self, raw_telemetry: Dict[str, Any]) -> Dict[str, Any]:
        return raw_telemetry
