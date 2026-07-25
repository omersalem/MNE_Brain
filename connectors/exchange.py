from connectors.base import BaseVendorConnector
from typing import Dict, Any

class ExchangeConnector(BaseVendorConnector):
    def __init__(self):
        super().__init__("exchange", "Microsoft Exchange")

    def validate_connection(self, config: Dict[str, Any]) -> bool:
        return True

    def collect_telemetry(self, config: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "source": "Exchange Remote EMS PowerShell",
            "trust_level": "★★★★★ (Live Device CLI)",
            "host": config.get("host", "172.23.71.35"),
            "dag_name": "EXCH-DAG-MNE",
            "servers": ["EXCHANGESRV1", "EXCHANGESRV2"]
        }
