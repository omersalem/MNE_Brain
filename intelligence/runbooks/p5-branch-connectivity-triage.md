---
runbook_id: "p5-branch-connectivity-triage"
title: "Branch Connectivity Evidence Triage"
version: "1.0.0"
status: "operationally_reviewed"
runbook_type: "domain_troubleshooting"
scope_categories: ["network"]
scope_services: ["branch-routing", "ipsec-vpn", "firewall", "sd-wan"]
scope_entity_ids: ["fw-fortigate-bethlehem-01", "fw-fortigate-gaza-01", "fw-fortigate-hebron-01", "fw-fortigate-jenin-01", "fw-fortigate-jericho-01", "fw-fortigate-khanyounis-01", "fw-fortigate-nablus-01", "fw-fortigate-qalqilya-01", "fw-fortigate-rafah-01", "fw-fortigate-ramallah-01", "fw-fortigate-salfit-01", "fw-fortigate-tubas-01", "fw-fortigate-tulkarm-01", "rtr-tulkarm-01", "sw-cisco-jenin-01", "sw-cisco-tulkarm-01"]
category_fallback_allowed: false
owner_team: "MNE-BRAIN-OWNER"
requires_exact_target: true
live_access_allowed: false
remediation_allowed: false
evidence_objectives: ["confirm-affected-branch", "collect-branch-edge-reachability", "collect-tunnel-state", "collect-underlay-state", "collect-hq-path-state"]
stop_conditions: ["Affected branch is unknown", "HQ and branch targets are not exact", "The owner has not explicitly said proceed for read-only collection", "Local power or carrier state is unknown and requires on-site confirmation", "Evidence is stale, simulated, malformed, or cross-target", "A tunnel, route, policy, or remediation change is proposed without explicit owner instruction"]
source_basis: "owner_review"
review_sources: ["BRANCH_CONNECTIVITY_BASELINE.md", "MASTER_ASSET_INVENTORY.md"]
operational_boundary: "PROCEDURE_REVIEWED_LIVE_STATE_UNVERIFIED"
last_reviewed: "2026-08-16"
---

# Branch Connectivity Evidence Triage

## Evidence sequence

1. Name the branch, exact edge entity, affected services, population, and time window.
2. Separate local power/LAN reports, branch-edge reachability, carrier underlay, VPN state, routing, and HQ-side policy.
3. Compare branch and HQ observations only when attributable and time-aligned.
4. Distinguish a single-service symptom from branch-wide or multi-branch impact.
5. Stop at the first unresolved prerequisite or any proposed change.

## Decision boundaries

A user report alone does not establish a carrier, tunnel, firewall, switching, or power fault. A tunnel-up observation does not prove application reachability, and an HQ-side observation does not prove the branch-side state.

## Owner handoff

Return branch, exact targets, affected scope, accepted evidence, local confirmation gaps, and the next smallest objective to `MNE-BRAIN-OWNER`. On-site coordination is a suggestion only; this system does not notify or assign anyone.
