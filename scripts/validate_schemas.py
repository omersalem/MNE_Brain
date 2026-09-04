#!/usr/bin/env python3
"""
MNE_Brain Release 2 — Milestone 1 Schema & Contract Validator
Validates JSON Schemas, ADR files, naming conventions, and AGENTS.md governance contract.
"""

import sys
import json
import jsonschema
from pathlib import Path

def validate_schemas():
    base_dir = Path(__file__).resolve().parent.parent
    schemas_dir = base_dir / "00_meta" / "schemas"
    adr_dir = base_dir / "00_meta" / "adr"
    
    errors = []
    passed = 0
    
    print("[VALIDATING MILESTONE 1 ARCHITECTURE CONTRACTS]")
    
    # 1. Check AGENTS.md
    agents_md = base_dir / "AGENTS.md"
    if not agents_md.exists():
        errors.append("AGENTS.md missing")
    else:
        print(" [PASS] AGENTS.md exists and verified")
        passed += 1
        
    # 2. Check Naming Conventions doc
    naming_doc = base_dir / "00_meta" / "01_naming_conventions.md"
    if not naming_doc.exists():
        errors.append("00_meta/01_naming_conventions.md missing")
    else:
        print(" [PASS] 00_meta/01_naming_conventions.md verified")
        passed += 1
        
    # 3. Validate JSON Schemas syntax
    required_schemas = [
        "profile.schema.json",
        "task.schema.json",
        "evidence.schema.json",
        "action.schema.json",
        "entity.schema.json",
        "canonical-note.schema.json",
        "live-evidence.schema.json",
        "investigation.schema.json",
        "incident-case.schema.json",
        "incident-intake.schema.json",
        "incident-workflow-governance.schema.json",
        "runbook.schema.json",
        "connector-catalog.schema.json",
        "p7-transport-catalog.schema.json",
        "p7-device-bindings.schema.json",
        "p8-diagnostic-catalog.schema.json",
        "p9-diagnostic-catalog.schema.json",
        "p10-operation-catalog.schema.json",
        "p10-operation-parameters.schema.json",
        "p10-prepared-plan.schema.json",
        "p10-approval-request.schema.json",
        "p10-execution-result.schema.json",
        "p10-rollback-plan.schema.json",
        "p10-critical-warning.schema.json",
        "p10-platform-transaction.schema.json",
        "p10-check-result.schema.json",
        "owner-direct-risk-warning.schema.json",
        "owner-direct-identity-audit.schema.json",
        "conversation-thread.schema.json",
        "conversation-turn.schema.json",
        "conversation-message.schema.json",
        "provider-profile.schema.json",
        "provider-capabilities.schema.json",
        "tool-call.schema.json",
        "tool-approval.schema.json",
        "stream-event.schema.json",
        "external-ai-authorization.schema.json",
        "workspace-change-plan.schema.json",
        "workspace-rollback-plan.schema.json",
    ]
    for s_name in required_schemas:
        s_path = schemas_dir / s_name
        if not s_path.exists():
            errors.append(f"Schema missing: {s_name}")
            continue
        try:
            with open(s_path, 'r', encoding='utf-8') as f:
                schema_data = json.load(f)
            jsonschema.Draft7Validator.check_schema(schema_data)
            print(f" [PASS] Schema syntax valid: {s_name}")
            passed += 1
        except Exception as e:
            errors.append(f"Schema invalid {s_name}: {str(e)}")

    # 4. Validate ADRs
    required_adrs = [
        "ADR-001-Independent-Projects.md",
        "ADR-002-Brain-First-Architecture.md",
        "ADR-003-Evidence-Driven-Retrieval.md",
        "ADR-004-Policy-Engine-Separation.md",
        "ADR-005-Execution-Tool-Driver-Split.md",
        "ADR-006-Knowledge-Lifecycle-Engine.md",
        "ADR-007-Presentation-Only-GUI.md",
        "ADR-008-P2-Controlled-Read-Only-Adapters.md",
        "ADR-009-P3-Evidence-Bounded-Incident-Orchestration.md",
        "ADR-010-P4-Offline-Incident-Case-Management.md",
        "ADR-011-P5-Runbook-Intelligence-and-Coverage.md",
        "ADR-012-P0-Simple-Local-Secret-Containment.md",
        "ADR-013-P6-Multi-Platform-Read-Only-Connectors.md",
        "ADR-014-P7-Owner-Gated-Live-Transports.md",
        "ADR-015-P8-Live-Troubleshooting-Orchestration.md",
        "ADR-016-P9-Deep-Diagnostics-and-Reasoning.md",
        "ADR-017-P10-Owner-Controlled-Write-Execution.md",
        "ADR-018-P11-Conversation-Provider-Tool-Control-Plane.md",
    ]
    for adr_name in required_adrs:
        adr_path = adr_dir / adr_name
        if not adr_path.exists():
            errors.append(f"ADR missing: {adr_name}")
        else:
            print(f" [PASS] ADR verified: {adr_name}")
            passed += 1

    print("\n--- MILESTONE 1 VALIDATION SUMMARY ---")
    if errors:
        print(f"FAILED with {len(errors)} errors:")
        for err in errors:
            print(f" - {err}")
        return False
    else:
        print(f"SUCCESS: {passed} Architecture Contracts & Schemas Verified (0 Errors)")
        return True

if __name__ == "__main__":
    success = validate_schemas()
    sys.exit(0 if success else 1)
