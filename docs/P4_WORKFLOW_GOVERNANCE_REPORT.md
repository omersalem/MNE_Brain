# P4 Sole-Owner Governance Report

**Date:** 2026-08-16  
**Result:** Simplified sole-owner boundary implemented  
**Approval state:** `OWNER_CONTROLLED`

## Active model

```yaml
approval_state: OWNER_CONTROLLED
owner_reference: MNE-BRAIN-OWNER
audit_mode: IN_MEMORY_ONLY
retention: NONE
ticketing_enabled: false
paging_enabled: false
notifications_enabled: false
automatic_assignment_enabled: false
automatic_remediation_enabled: false
```

There are no workflow-owner, operations-owner, security-approver, or audit-retention approval references. No replacement approval system exists.

The same rule now governs P2 read-only activation, remediation planning, the execution foundation, knowledge-review promotion, incident intake, runbook ownership, and the GUI. Legacy operator/team inputs, approval contexts, timestamped approval records, authorization references, and persistent-audit prerequisites were removed.

## Authorization rules

- The owner is the only operator, administrator, and approver.
- Read-only troubleshooting may proceed after the owner explicitly says `proceed`.
- Configuration changes and remediation require explicit owner instructions.
- Persistent incident or audit storage requires an explicit owner request.
- Secrets may remain in the ignored local `.env` file.
- The remediation API accepts only `owner_reference: MNE-BRAIN-OWNER` plus `explicit_owner_instruction: true`; it remains planning-only and cannot construct a driver.
- Knowledge proposals remain in memory unless persistence is explicitly requested; manual promotion review uses the fixed owner and never edits canonical knowledge automatically.

## Disabled capabilities

- automatic assignment;
- automatic remediation;
- notifications;
- ticketing;
- paging;
- persistent incident and audit storage.

`GET /api/incidents/workflow/status` returns this global policy and accepts no target, team, approver, or approval-reference input.

## Acceptance evidence

- Sole-owner governance pilot: 10/10 scenarios passed.
- Attempts to enable notification or persistent retention through policy drift failed closed.
- Assignment actions: 0.
- Notifications: 0.
- Persistence actions: 0.
- Remediation actions: 0.
- Architecture/schema validation: 26/26 passed.
- Master validation: 19/19 passed.
- Evidence-flow benchmarks: 11/11 passed.
- Complete pytest regression: 60/60 passed.
- Python syntax: 86/86 files passed.
- GUI inline JavaScript syntax and local HTTP governance/intake smoke checks passed.
- Four pre-existing legacy persistence artifacts (`audit_log.json`, `review_queue.json`, `verification_history.json`, and `observability.jsonl`) were removed to enforce `retention: NONE`; verification fixtures were preserved.
