# P4 Professional Incident Intake Report

**Date:** 2026-08-16  
**Result:** Implemented and accepted offline  
**External side effects:** None

## Delivered capability

The P4 intake path now provides:

- a strict request schema at `00_meta/schemas/incident-intake.schema.json`;
- deterministic validation in `core/incidents/intake.py`;
- a dedicated `POST /api/incidents/intake` endpoint;
- a presentation-only operator form in the evidence console;
- preservation of reported facts as `REPORTED_NOT_VERIFIED`;
- exact-target and assessed-impact gates before evidence objectives are returned;
- automatic application of the sole owner `MNE-BRAIN-OWNER`;
- no live connection, notification, persistence, or remediation.
- an embedded sole-owner governance result with no additional approval blockers.

## Required request fields

| Field | Purpose |
|---|---|
| `target_reference` | Canonical entity ID, hostname, address, or other resolvable target reference |
| `symptom` | What the operator or users observe |
| `affected_service` | Service whose availability is affected |
| `affected_scope` | User, branch, multi-branch, or ministry scope |
| `availability` | Unavailable, degraded, intermittent, or unknown |
| `reported_at` | Timezone-aware observation/report timestamp |

Branch references, affected user count, security/data-loss/public-service flags, and incident reference are optional but validated when supplied. The operator/owner reference is automatically `MNE-BRAIN-OWNER`.

## Readiness outcomes

| Outcome | Meaning |
|---|---|
| `NEEDS_TARGET` | Target did not resolve exactly; evidence objectives are withheld |
| `IMPACT_REQUIRED` | Scope and availability remain unassessed; evidence objectives are withheld |
| `READY_FOR_EVIDENCE_REVIEW` | Target and reported impact are sufficient to present bounded read-only evidence objectives for operator review |

None of these outcomes verifies the report or authorizes collection.

## Acceptance evidence

- Professional intake pilot: 12/12 scenarios passed.
- Local REST smoke test: HTTP 200.
- Example accepted state: `READY_FOR_EVIDENCE_REVIEW` / `AWAITING_EVIDENCE` / `PROVISIONAL_P2`.
- Invalid branch/user combinations, future timestamps, control characters, extra fields, and unknown targets failed closed.
- Sole ownership was applied without any department routing or notification.
- Live connections: 0.
- Notifications: 0.
- Persistence actions: 0.
- Remediation actions: 0.
