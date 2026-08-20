---
runbook_id: "p5-messaging-triage"
title: "Messaging Service Evidence Triage"
version: "1.0.0"
status: "operationally_reviewed"
runbook_type: "domain_troubleshooting"
scope_categories: ["compute", "messaging"]
scope_services: ["smtp-25", "submission-587", "imaps-993", "owa-https", "dag-replication"]
scope_entity_ids: ["ex-windows-mail-01", "ex-windows-mail-02"]
category_fallback_allowed: false
owner_team: "MNE-BRAIN-OWNER"
requires_exact_target: true
live_access_allowed: false
remediation_allowed: false
evidence_objectives: ["confirm-messaging-symptom", "collect-name-resolution-state", "collect-client-endpoint-state", "collect-transport-service-state", "collect-mailbox-service-state", "collect-replication-state"]
stop_conditions: ["Affected protocol or user population is unknown", "The owner has not explicitly said proceed for read-only collection", "Message content or personal data would enter evidence", "Client, transport, mailbox, or DAG evidence is stale, simulated, malformed, or cross-target", "A queue, database, service, DAG, configuration, or remediation change is proposed without explicit owner instruction"]
source_basis: "owner_review"
review_sources: ["MASTER_ASSET_INVENTORY.md", "SERVER_FLEET_BASELINE.md"]
operational_boundary: "PROCEDURE_REVIEWED_LIVE_STATE_UNVERIFIED"
last_reviewed: "2026-08-16"
---

# Messaging Service Evidence Triage

## Evidence sequence

1. Fix the exact Exchange entity, affected protocol, client population, direction, and time window.
2. Separate DNS/client path, published endpoint, submission, transport, mailbox service, queues, databases, and DAG replication.
3. Use synthetic or opaque references; do not include message bodies, addresses, credentials, or personal data.
4. Correlate observations only when they cover the same protocol and time window.
5. Stop before queue, database, service, connector, DAG, or configuration actions.

## Decision boundaries

A successful check at one layer does not prove end-to-end mail health. A queue observation does not prove its cause, and DAG state does not prove client access or delivery.

## Owner handoff

Return exact target, protocol, reported scope, timestamps, accepted evidence, remaining unknowns, and next objective to `MNE-BRAIN-OWNER`.
