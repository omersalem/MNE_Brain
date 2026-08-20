---
runbook_id: "p5-compute-application-triage"
title: "Compute and Application Evidence Triage"
version: "1.0.0"
status: "operationally_reviewed"
runbook_type: "domain_troubleshooting"
scope_categories: ["compute", "application"]
scope_services: ["internal-portal", "auction-portal", "apdct-service", "n8n-workflows", "webhook-listener", "api-integrations", "network-printing", "ipp", "raw-jetdirect-9100"]
scope_entity_ids: ["app-apdct-web-01", "app-auction-test-01", "n8n-automation-server-01", "prt-jenin-office-01", "web-greenunit-ubuntu-01"]
category_fallback_allowed: true
owner_team: "MNE-BRAIN-OWNER"
requires_exact_target: true
live_access_allowed: false
remediation_allowed: false
evidence_objectives: ["confirm-application-symptom", "collect-target-reachability", "collect-service-state", "collect-local-dependency-state", "collect-network-path-state", "collect-upstream-dependency-state"]
stop_conditions: ["Application, service, or compute target is unknown", "The owner has not explicitly said proceed for read-only collection", "User report is being treated as service state", "Dependency evidence is stale, simulated, malformed, cross-target, or inferred from documentation", "A restart, deployment, configuration, data change, or remediation is proposed without explicit owner instruction"]
source_basis: "owner_review"
review_sources: ["SERVER_FLEET_BASELINE.md", "server-vm-and-ssh.md"]
operational_boundary: "PROCEDURE_REVIEWED_LIVE_STATE_UNVERIFIED"
last_reviewed: "2026-08-16"
---

# Compute and Application Evidence Triage

## Evidence sequence

1. Fix the exact application/compute entity, service endpoint, user impact, and time window.
2. Separate host reachability, process/service state, local resources, network path, and upstream dependencies.
3. Start at the narrowest layer able to reproduce or distinguish the reported symptom.
4. Treat documentation and user reports as context until supported by attributable evidence.
5. Stop before restart, deployment, data, dependency, or configuration actions.

## Decision boundaries

Reachability does not prove service health, a running process does not prove correct responses, and an upstream alarm does not prove causality. Missing dependency evidence remains `UNKNOWN`.

## Owner handoff

Return exact endpoint and entity, reported impact, evidence references, supported and rejected hypotheses, unknowns, and next bounded objective to `MNE-BRAIN-OWNER`.
