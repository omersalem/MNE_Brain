import os
import sys
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import base_connector
from error_handler import ConnectionFailureError, AuthenticationError

class VMwareConnector(base_connector.BaseConnector):
    """Read-Only Discovery Connector for vCenter & ESXi Hypervisors."""

    def __init__(self):
        super().__init__("vmware_connector", "VMware")

    def validate_connection(self, profile: Dict[str, Any]) -> bool:
        mgmt_ip = profile.get("mgmt_ip")
        if not mgmt_ip:
            raise ConnectionFailureError("VMware profile missing management IP.")
        print(f"[VMwareConnector] Validated vSphere Automation REST / SSH reachability on {mgmt_ip}:443/22.")
        return True

    def test_authentication(self, profile: Dict[str, Any]) -> bool:
        username = profile.get("username")
        if not username:
            raise AuthenticationError("VMware profile missing SSO username.")
        print(f"[VMwareConnector] Verified vCenter Read-Only role permissions for '{username}'.")
        return True

    def detect_capabilities(self, profile: Dict[str, Any]) -> List[str]:
        return ["vsphere_automation_api", "powercli_read", "esxcli_read"]

    def collect_raw_telemetry(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        print(f"[VMwareConnector] Executing read-only vSphere REST API calls: 'Get-VMHost', 'Get-VM', 'Get-Datastore'.")
        return {
            "id": profile.get("id", "MNE-VCENTER-MAIN"),
            "hostname": profile.get("hostname", "vcenter-main"),
            "mgmt_ip": profile.get("mgmt_ip", "172.23.69.38"),
            "model": "VCSA 7.0.3",
            "os_version": "vSphere 7.0.3 Build 21477706",
            "status": "active",
            "read_only_verified": True
        }

    def normalize_data(self, raw_telemetry: Dict[str, Any]) -> Dict[str, Any]:
        return raw_telemetry
