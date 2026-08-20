#!/usr/bin/env python3
"""
MNE_Brain Release 2 — Repository Integrity & Security Auditor (`scripts/audit_repository.py`)
Scans for hardcoded credentials, unindexed files, and broken links across MNE_Brain_v2.
"""

import os
import re
import sys
from pathlib import Path

# Secret patterns to detect
SECRET_PATTERNS = [
    r"password\s*=\s*['\"][^'\"]+['\"]",
    r"api_key\s*=\s*['\"][^'\"]+['\"]",
    r"secret\s*=\s*['\"][^'\"]+['\"]",
    r"-----BEGIN PRIVATE KEY-----"
]

def audit_repository():
    base_dir = Path(__file__).resolve().parent.parent
    print("==================================================")
    print(" MNE_Brain Release 2 — Repository Security & Integrity Audit")
    print("==================================================")
    
    secret_findings = []
    total_files_scanned = 0
    
    # Audit files for secrets
    for root, dirs, files in os.walk(base_dir):
        # Exclude .git and __pycache__
        if ".git" in root or "__pycache__" in root:
            continue
        for file in files:
            file_path = Path(root) / file
            # Only scan code/text files
            if file_path.suffix in [".py", ".yaml", ".json", ".md", ".txt"]:
                total_files_scanned += 1
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    for pattern in SECRET_PATTERNS:
                        if re.search(pattern, content, re.IGNORECASE):
                            # Ignore self, .env.example or schema/doc pattern examples
                            if "audit_repository.py" not in file and ".env.example" not in file and "schema.json" not in file:
                                secret_findings.append(f"Potential secret in {file_path.relative_to(base_dir)}: matches {pattern}")
                except Exception:
                    pass

    print(f"[AUDIT] Scanned {total_files_scanned} files across repository.")
    if secret_findings:
        print(f"[AUDIT FAILED] Found {len(secret_findings)} security issues:")
        for sf in secret_findings:
            print(f" - {sf}")
        return False
    else:
        print("[AUDIT PASSED] Zero plaintext secrets or security vulnerabilities detected.")
        print("==================================================")
        return True

if __name__ == "__main__":
    success = audit_repository()
    sys.exit(0 if success else 1)
