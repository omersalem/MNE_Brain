from typing import Dict, Any

class DataNormalizer:
    """Normalizes vendor-specific telemetry into Ministry schemas."""

    @staticmethod
    def normalize_device(vendor: str, raw: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": raw.get("id", f"MNE-DEV-{raw.get('hostname', 'UNKNOWN').upper()}"),
            "hostname": raw.get("hostname", "unknown"),
            "mgmt_ip": raw.get("mgmt_ip", "0.0.0.0"),
            "vendor": vendor,
            "model": raw.get("model", "Generic"),
            "os_version": raw.get("os_version", "Unknown"),
            "status": raw.get("status", "active"),
            "interfaces": raw.get("interfaces", []),
            "vlans": raw.get("vlans", []),
            "services": raw.get("services", []),
            "confidence_score": 1.0
        }
