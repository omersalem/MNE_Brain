---
runbook_id: "p5-network-infrastructure-triage"
title: "Network Infrastructure Evidence Triage"
version: "1.0.0"
status: "operationally_reviewed"
runbook_type: "domain_troubleshooting"
scope_categories: ["network"]
scope_services: ["switching", "routing", "firewall", "vlan-routing", "trunking", "poe+"]
scope_entity_ids: ["fw-fortigate-edge-01", "fw-fortigate-hq-01", "sw-cisco-core-01", "sw-cisco-floor-1", "sw-cisco-floor-2", "sw-cisco-floor-3", "sw-cisco-floor-4", "sw-cisco-floor-5", "sw-cisco-floor-6", "sw-cisco-floor-b1", "sw-cisco-floor-gnd", "sw-cisco-floor-svc", "sw-cisco-jenin-01"]
category_fallback_allowed: true
owner_team: "MNE-BRAIN-OWNER"
requires_exact_target: true
live_access_allowed: false
remediation_allowed: false
evidence_objectives: ["confirm-reported-flow", "collect-target-reachability", "collect-interface-state", "collect-route-state", "collect-adjacent-path-state"]
stop_conditions: ["Source, destination, or required service is unknown", "Target identity is ambiguous", "The owner has not explicitly said proceed for read-only collection", "Evidence is stale, simulated, malformed, or cross-target", "A configuration change or remediation is proposed without explicit owner instruction"]
source_basis: "owner_review"
review_sources: ["MASTER_ASSET_INVENTORY.md", "MAIN_DEVICE_LINK_PORT_DISCOVERY.md"]
operational_boundary: "PROCEDURE_REVIEWED_LIVE_STATE_UNVERIFIED"
last_reviewed: "2026-08-16"
---

# Network Infrastructure Evidence Triage

## Evidence sequence

1. Fix the source, destination, protocol, service, exact entity, time window, and reported impact.
2. Separate physical/interface state, Layer-2 adjacency, Layer-3 reachability, and policy enforcement.
3. Collect one minimal, attributable observation at the earliest unknown layer.
4. Compare adjacent devices only when their observations are time-aligned and target-scoped.
5. Stop when evidence conflicts or the next step would change configuration.

## Decision boundaries

A documented VLAN, trunk, route, or link is context, not proof of current state. A reachable device does not prove the reported flow works, and a down interface does not prove it is part of the affected path.

## Owner handoff

Return the exact flow, entity, reported impact, supported and conflicting evidence, remaining unknowns, and next bounded objective to `MNE-BRAIN-OWNER`. Read-only collection requires `proceed`; any VLAN, route, interface, policy, PoE, or reset action requires a separate explicit instruction.
