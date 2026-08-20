---
runbook_id: "p5-virtualization-triage"
title: "Virtualization Platform Evidence Triage"
version: "1.0.0"
status: "operationally_reviewed"
runbook_type: "domain_troubleshooting"
scope_categories: ["compute"]
scope_services: ["vcenter", "vsphere", "esxi-management", "vmware-esxi", "host-management", "vmotion", "vsan"]
scope_entity_ids: ["vc-vmware-hq-01", "esxi-node-hq-01", "esxi-node-hq-02"]
category_fallback_allowed: false
owner_team: "MNE-BRAIN-OWNER"
requires_exact_target: true
live_access_allowed: false
remediation_allowed: false
evidence_objectives: ["confirm-workload-scope", "collect-management-plane-state", "collect-host-state", "collect-guest-state", "collect-datastore-state", "collect-network-dependency-state"]
stop_conditions: ["Affected guest, host, cluster, or management target is unknown", "The owner has not explicitly said proceed for read-only collection", "Inventory evidence is stale, simulated, malformed, cross-target, or unattributed", "Storage and network dependencies are being inferred", "A power, placement, snapshot, failover, configuration, or remediation action is proposed without explicit owner instruction"]
source_basis: "owner_review"
review_sources: ["MASTER_ASSET_INVENTORY.md", "SERVER_FLEET_BASELINE.md", "vmware-build-and-onboard.md"]
operational_boundary: "PROCEDURE_REVIEWED_LIVE_STATE_UNVERIFIED"
last_reviewed: "2026-08-16"
---

# Virtualization Platform Evidence Triage

## Evidence sequence

1. Fix the exact vCenter/ESXi target, guest or service impact, and time window.
2. Separate management-plane reachability, host state, guest state, virtual networking, and datastore dependencies.
3. Treat inventory and documented adjacency as context until freshly observed.
4. Compare vCenter and host observations only when target- and time-aligned.
5. Stop before power, migration, snapshot, placement, failover, storage, or network changes.

## Decision boundaries

Inventory presence does not establish workload health. A reachable vCenter does not prove host, guest, network, or datastore health, and an alarm does not prove causality.

## Owner handoff

Return exact platform and workload scope, evidence references, dependency unknowns, and the next bounded objective to `MNE-BRAIN-OWNER`. Related storage or network checks remain separate owner-controlled scopes.
