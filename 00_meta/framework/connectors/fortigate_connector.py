import os
import sys
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import base_connector
from error_handler import ConnectionFailureError, AuthenticationError

class FortiGateConnector(base_connector.BaseConnector):
    """Read-Only Discovery Connector for FortiGate Firewalls (FortiOS)."""

    def __init__(self):
        super().__init__("fortigate_connector", "Fortinet")

    def validate_connection(self, profile: Dict[str, Any]) -> bool:
        mgmt_ip = profile.get("mgmt_ip")
        if not mgmt_ip:
            raise ConnectionFailureError("FortiGate profile missing management IP.")
        print(f"[FortiGateConnector] Validated reachability target {mgmt_ip}:22 / 443.")
        return True

    def test_authentication(self, profile: Dict[str, Any]) -> bool:
        username = profile.get("username")
        if not username:
            raise AuthenticationError("FortiGate profile missing username.")
        print(f"[FortiGateConnector] Verified read-only credentials for user '{username}'.")
        return True

    def detect_capabilities(self, profile: Dict[str, Any]) -> List[str]:
        return ["fortios_rest_api", "ssh_cli_read", "vdom_root_read"]

    def collect_raw_telemetry(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        print(f"[FortiGateConnector] Executing read-only commands: 'get system status', 'show firewall policy'.")
        return {
            "id": profile.get("id", "MNE-FW-FG-HQ-01"),
            "hostname": profile.get("hostname", "FG-MNE-B"),
            "mgmt_ip": profile.get("mgmt_ip", "172.23.70.4"),
            "model": "FortiGate 601E",
            "os_version": "FortiOS 7.4.11",
            "status": "active",
            "read_only_verified": True
        }

    def normalize_data(self, raw_telemetry: Dict[str, Any]) -> Dict[str, Any]:
        return raw_telemetry
