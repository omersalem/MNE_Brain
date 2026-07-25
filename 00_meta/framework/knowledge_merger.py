import re
import yaml
from typing import Dict, Any, List

class KnowledgeMerger:
    """Updates YAML frontmatter & preserves human prose."""

    @staticmethod
    def merge_into_markdown(existing_md: str, updates: Dict[str, Any], changes: List[Dict[str, Any]]) -> str:
        fm_match = re.search(r"^---\s*\n(.*?)\n---", existing_md, re.DOTALL)
        if not fm_match:
            return existing_md

        try:
            fm_data = yaml.safe_load(fm_match.group(1)) or {}
        except Exception:
            fm_data = {}

        for c in changes:
            fm_data[c["field"]] = c["new_value"]

        fm_data["last_verified"] = "2026-07-24"
        fm_data["confidence_score"] = 1.0

        new_fm_str = yaml.dump(fm_data, default_flow_style=False).strip()
        body = existing_md[fm_match.end():]

        return f"---\n{new_fm_str}\n---" + body
