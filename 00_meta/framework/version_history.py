import os
import json
from datetime import datetime
from typing import Dict, Any, List

class VersionHistory:
    """Maintains an append-only revision history of all Digital Twin updates."""

    def __init__(self, vault_root: str):
        self.log_file = os.path.join(vault_root, "80_ai_knowledge", "version_history.jsonl")

    def record_change(self, entity_id: str, field: str, old_val: Any, new_val: Any, source: str, confidence: float):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "entity_id": entity_id,
            "field": field,
            "old_value": old_val,
            "new_value": new_val,
            "source": source,
            "confidence": confidence
        }
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        print(f"[VersionHistory] Logged change for {entity_id}: {field}")
