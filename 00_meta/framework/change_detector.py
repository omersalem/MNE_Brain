from typing import Dict, Any, List

class ChangeDetector:
    """Evaluates diffs between newly collected telemetry and vault state."""

    @staticmethod
    def detect_changes(vault_state: Dict[str, Any], telemetry_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        changes = []

        for key in ["mgmt_ip", "model", "os_version", "status"]:
            v_val = vault_state.get(key)
            t_val = telemetry_state.get(key)
            if t_val and v_val != t_val:
                changes.append({
                    "field": key,
                    "old_value": v_val,
                    "new_value": t_val,
                    "type": "ATTRIBUTE_DRIFT"
                })

        return changes
