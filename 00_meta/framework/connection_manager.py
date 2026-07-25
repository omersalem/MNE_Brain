import os
import re
import yaml
from typing import Dict, Any
from error_handler import ConnectionFailureError, AuthenticationError

class ConnectionManager:
    """Reads, parses, and validates Connection Profiles from vault."""

    def __init__(self, vault_root: str):
        self.vault_root = vault_root
        self.connections_dir = os.path.join(vault_root, "00_meta", "05_connections")

    def load_profile(self, profile_rel_path: str) -> Dict[str, Any]:
        full_path = os.path.join(self.vault_root, profile_rel_path)
        if not os.path.exists(full_path):
            raise ConnectionFailureError(f"Connection Profile file not found: {profile_rel_path}")

        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        profile = {"path": profile_rel_path}
        
        # Parse YAML frontmatter
        fm_match = re.search(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if fm_match:
            try:
                fm = yaml.safe_load(fm_match.group(1))
                if isinstance(fm, dict):
                    profile.update(fm)
            except Exception:
                pass

        # Parse key-value bullet points
        kv_patterns = {
            "mgmt_ip": r"\*\*Management IP:\*\*\s*`?([^\n`]+)`?",
            "username": r"\*\*Username:\*\*\s*`?([^\n`]+)`?",
            "password": r"\*\*Password:\*\*\s*`?([^\n`]+)`?",
            "port": r"\*\*Port:\*\*\s*`?([^\n`]+)`?",
            "protocol": r"\*\*Protocol:\*\*\s*`?([^\n`]+)`?",
            "domain": r"\*\*Domain:\*\*\s*`?([^\n`]+)`?"
        }

        for key, pattern in kv_patterns.items():
            match = re.search(pattern, content)
            if match and key not in profile:
                profile[key] = match.group(1).strip()

        self.validate_profile(profile)
        return profile

    def validate_profile(self, profile: Dict[str, Any]):
        mgmt_ip = profile.get("mgmt_ip")
        if not mgmt_ip or "PENDING" in str(mgmt_ip):
            raise ConnectionFailureError(f"Profile {profile.get('path')} missing valid Management IP.")

        username = profile.get("username")
        if not username or "PENDING" in str(username):
            raise AuthenticationError(f"Profile {profile.get('path')} missing valid Username.")
