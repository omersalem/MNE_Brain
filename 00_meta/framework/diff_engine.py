import re
import yaml
from typing import Dict, Any, List

class DiffEngine:
    """Compares vault state against new knowledge sources and classifies diffs."""

    CHANGE_TYPES = [
        "NEW_DEVICE", "REMOVED_DEVICE", "CONFIGURATION_CHANGE",
        "FIRMWARE_UPGRADE", "TOPOLOGY_CHANGE", "RELATIONSHIP_CHANGE",
        "DOCUMENTATION_IMPROVEMENT", "METADATA_UPDATE", "OUTDATED_DOCUMENTATION"
    ]

    @staticmethod
    def compare_states(vault_state: Dict[str, Any], new_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        diffs = []
        
        # Check firmware / version upgrades
        v_fw = vault_state.get("firmware_version") or vault_state.get("os_version")
        n_fw = new_state.get("firmware_version") or new_state.get("os_version")
        if v_fw and n_fw and v_fw != n_fw:
            diffs.append({
                "field": "os_version",
                "old_value": v_fw,
                "new_value": n_fw,
                "type": "FIRMWARE_UPGRADE",
                "confidence": 0.95
            })

        # Check IP / Network topology shifts
        v_ip = vault_state.get("mgmt_ip")
        n_ip = new_state.get("mgmt_ip")
        if v_ip and n_ip and v_ip != n_ip:
            diffs.append({
                "field": "mgmt_ip",
                "old_value": v_ip,
                "new_value": n_ip,
                "type": "TOPOLOGY_CHANGE",
                "confidence": 0.90
            })

        # Check general attributes
        for key in ["status", "owner", "model", "site"]:
            if key in new_state and new_state[key] != vault_state.get(key):
                diffs.append({
                    "field": key,
                    "old_value": vault_state.get(key),
                    "new_value": new_state[key],
                    "type": "CONFIGURATION_CHANGE",
                    "confidence": 0.85
                })

        return diffs
