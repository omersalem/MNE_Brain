from typing import Dict, Any, List

class BaseVendorConnector:
    def __init__(self, platform_id: str, vendor_name: str):
        self.platform_id = platform_id
        self.vendor_name = vendor_name

    def validate_connection(self, config: Dict[str, Any]) -> bool:
        raise NotImplementedError

    def collect_telemetry(self, config: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def normalize(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        return raw_data
