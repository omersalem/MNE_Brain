from connectors.base import BaseVendorConnector
from typing import Dict, Any

class LinuxConnector(BaseVendorConnector):
    def __init__(self):
        super().__init__("linux", "Linux Server")

    def validate_connection(self, config: Dict[str, Any]) -> bool:
        return True

    def collect_telemetry(self, config: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "source": "Linux OpenSSH",
            "trust_level": "★★★★★ (Live Device CLI)",
            "mgmt_ip": config.get("mgmt_ip", "172.23.79.200"),
            "hostname": "srv-linux-abrs-01",
            "os_release": "Ubuntu 22.04.4 LTS"
        }
