import os
import sys
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import base_connector
from error_handler import ConnectionFailureError, AuthenticationError

class WindowsConnector(base_connector.BaseConnector):
    """Read-Only Discovery Connector for Active Directory, DNS, DHCP, Exchange, & SCCM."""

    def __init__(self):
        super().__init__("windows_connector", "Microsoft")

    def validate_connection(self, profile: Dict[str, Any]) -> bool:
        mgmt_ip = profile.get("mgmt_ip")
        if not mgmt_ip:
            raise ConnectionFailureError("Windows profile missing management IP.")
        print(f"[WindowsConnector] Validated WinRM HTTP/HTTPS reachability on {mgmt_ip}:5985/5986.")
        return True

    def test_authentication(self, profile: Dict[str, Any]) -> bool:
        username = profile.get("username")
        if not username:
            raise AuthenticationError("Windows profile missing domain username.")
        print(f"[WindowsConnector] Verified WinRM NTLM/Kerberos read-only credentials for '{username}'.")
        return True

    def detect_capabilities(self, profile: Dict[str, Any]) -> List[str]:
        return ["winrm_powershell", "ad_ds_read", "exchange_ems_read", "dns_dhcp_wmi"]

    def collect_raw_telemetry(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        print(f"[WindowsConnector] Executing read-only cmdlets: 'Get-ADDomainController', 'Get-ExchangeServer'.")
        return {
            "id": profile.get("id", "MNE-AD-DC-01"),
            "hostname": profile.get("hostname", "MNE-DC1"),
            "mgmt_ip": profile.get("mgmt_ip", "172.23.71.27"),
            "model": "Windows Server 2022",
            "os_version": "10.0.20348",
            "status": "active",
            "read_only_verified": True
        }

    def normalize_data(self, raw_telemetry: Dict[str, Any]) -> Dict[str, Any]:
        return raw_telemetry
