---
runbook_id: "p4-incident-case-handoff"
title: "P4 Incident Case and Handoff"
version: "1.1.0"
status: "operationally_reviewed"
runbook_type: "handoff"
scope_categories: ["network", "compute", "storage", "identity", "messaging", "application"]
scope_services: []
scope_entity_ids: []
category_fallback_allowed: true
owner_team: "MNE-BRAIN-OWNER"
requires_exact_target: true
live_access_allowed: false
remediation_allowed: false
evidence_objectives: ["confirm-reported-impact", "confirm-human-priority", "review-pending-evidence-objectives"]
stop_conditions: ["Target is unknown", "Priority has not received owner confirmation", "The owner has not explicitly said proceed for read-only collection", "Evidence is stale, simulated, malformed, or cross-target", "A notification, persistence action, configuration change, or remediation is requested without explicit owner instruction"]
source_basis: "owner_review"
review_sources: ["AGENTS.md", "p4_incident_policy.yaml"]
operational_boundary: "PROCEDURE_REVIEWED_LIVE_STATE_UNVERIFIED"
last_reviewed: "2026-08-16"
---

# P4 Incident Case and Handoff Runbook

## Purpose

Use this runbook to prepare a consistent incident packet for `MNE-BRAIN-OWNER` without opening a ticket, paging anyone, collecting telemetry, or changing infrastructure.

## Required intake

Provide one exact target and, when known:

- affected scope: single user, multiple users, branch, multiple branches, or ministry-wide;
- availability: unavailable, degraded, or intermittent;
- whether security impact or data loss is suspected;
- whether a public service is affected;
- an opaque reporter or incident reference;
- a timezone-aware report timestamp.

Do not include personal data, credentials, commands, raw logs, or free-form secrets.

## Triage procedure

1. Confirm that P3 resolved exactly one target.
2. Review the normalized impact and verify it remains `REPORTED_NOT_VERIFIED`.
3. The sole owner reviews the provisional priority.
4. Keep ownership fixed to `MNE-BRAIN-OWNER`; do not route to departments.
5. Review remaining unknowns and pending evidence objectives.
6. Record an objective outcome only as `COLLECTED_REPORTED`, `FAILED_REPORTED`, or `SKIPPED_REPORTED`.
7. Do not treat a reported collected outcome or reference ID as verified evidence.
8. Continue the same case only when the case schema, question, and target match exactly.
9. Export the handoff packet to the authorized human workflow only after checking it for sensitive content.

## Stop conditions

Stop when the target is unknown, impact values are outside the allowlist, a timestamp is in the future, the prior case does not match, a check is outside the objective allowlist, an SLA is assumed, or any notification, persistence, live access, or remediation is requested.

## Human handoff

`MNE-BRAIN-OWNER` must confirm priority, explicitly say `proceed` for any read-only evidence collection, and explicitly instruct any configuration change or remediation. P4 creates no ticket, notification, page, assignment, SLA, or persistent incident record.
