#!/usr/bin/env python3
"""
MNE_Brain Release 2 — Phase F Security Validation Engine
Audits secret handling, input sanitization, path traversal resistance, and command injection safety.
"""

import sys
import re
from pathlib import Path

base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

from core.router.route_query import QueryRouter
from core.entity.build_entity_index import EntityIndexBuilder
from scripts.audit_repository import audit_repository

def test_security_validation():
    print("[RUNNING PHASE F — SECURITY VALIDATION SUITE]")
    errors = []
    passed = 0

    # 1. Plaintext Secrets & Vulnerability Audit
    if audit_repository():
        print(" [PASS] Plaintext Secrets & Credential Leak Audit PASSED (0 hardcoded secrets)")
        passed += 1
    else:
        errors.append("Plaintext secrets detected in repository")

    # 2. Path Traversal Resistance Test
    builder = EntityIndexBuilder(base_dir=base_dir)
    malicious_query = "../../etc/passwd"
    resolved = builder.resolve_entity(malicious_query)
    if not resolved:
        print(" [PASS] Path Traversal Query Injection resisted safely (0 unauthorized file access)")
        passed += 1
    else:
        errors.append("Path traversal vulnerability detected")

    # 3. Command Injection Safety Test
    router = QueryRouter(base_dir=base_dir)
    cmd_injection_query = "172.23.19.1; rm -rf / ; cat /etc/shadow"
    classified = router.classify_query(cmd_injection_query)
    if classified["route_type"] in ["asset", "troubleshoot"] and ";" not in classified["detected_asset_patterns"]:
        print(" [PASS] Command Injection Input Query sanitized cleanly")
        passed += 1
    else:
        errors.append("Command injection query sanitization failed")

    print("\n--- PHASE F SECURITY VALIDATION SUMMARY ---")
    if errors:
        print(f"FAILED with {len(errors)} errors:")
        for err in errors:
            print(f" - {err}")
        return False
    else:
        print(f"SUCCESS: {passed} Security Audit Scenarios Passed (0 Vulnerabilities)")
        return True

if __name__ == "__main__":
    success = test_security_validation()
    sys.exit(0 if success else 1)
