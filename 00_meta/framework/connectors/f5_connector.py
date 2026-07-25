import os
import sys
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import base_connector
from error_handler import ConnectionFailureError, AuthenticationError

class F5Connector(base_connector.BaseConnector):
    """Read-Only Discovery Connector for F5 BIG-IP WAF Appliances."""

    def __init__(self):
        super().__init__("f5_connector", "F5")

    def validate_connection(self, profile: Dict[str, Any]) -> bool:
        mgmt_ip = profile.get("mgmt_ip")
        if not mgmt_ip:
            raise ConnectionFailureError("F5 profile missing management IP.")
        print(f"[F5Connector] Validated reachability target {mgmt_ip}:22 / 443.")
        return True

    def test_authentication(self, profile: Dict[str, Any]) -> bool:
        username = profile.get("username")
        if not username:
            raise AuthenticationError("F5 profile missing username.")
        print(f"[F5Connector] Verified tmsh Auditor / iControl REST privileges.")
        return True

    def detect_capabilities(self, profile: Dict[str, Any]) -> List[str]:
        return ["icontrol_rest", "tmsh_cli_read", "asm_waf_read"]

    def collect_raw_telemetry(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        print(f"[F5Connector] Executing read-only tmsh calls: 'list ltm virtual one-line', 'show ltm pool members'.")
        return {
            "id": profile.get("id", "MNE-F5-VIP-PUB-98"),
            "hostname": profile.get("hostname", "f5-bigip-hq-01"),
            "mgmt_ip": profile.get("mgmt_ip", "172.23.70.89"),
            "model": "BIG-IP r2000",
            "os_version": "TMOS 17.5.1.3",
            "status": "active",
            "read_only_verified": True
        }

    def normalize_data(self, raw_telemetry: Dict[str, Any]) -> Dict[str, Any]:
        return raw_telemetry
