---
runbook_id: "p5-security-segmentation-triage"
title: "Cisco Security Policy and Segmentation Evidence Triage"
version: "1.0.0"
status: "operationally_reviewed"
runbook_type: "domain_troubleshooting"
scope_categories: ["network"]
scope_services: ["firepower-policy", "fmc-management", "ips-sensor-mgmt", "ftd-firewall", "malware-protection", "next-gen-ips", "vlan-filtering"]
scope_entity_ids: ["fmc-cisco-hq-01", "ftd-cisco-hq-01"]
category_fallback_allowed: false
owner_team: "MNE-BRAIN-OWNER"
requires_exact_target: true
live_access_allowed: false
remediation_allowed: false
evidence_objectives: ["confirm-reported-flow", "collect-management-plane-reachability", "collect-policy-deployment-state", "collect-access-control-decision-state", "collect-intrusion-event-state", "collect-adjacent-path-state"]
stop_conditions: ["Source, destination, protocol, service, or exact security target is unknown", "The owner has not explicitly said proceed for read-only collection", "FMC policy state is being treated as proof of FTD enforcement without attributable evidence", "Evidence is stale, simulated, malformed, cross-target, or from a different deployment", "A policy deploy, rule edit, intrusion action, configuration change, or remediation is proposed without explicit owner instruction"]
source_basis: "owner_review"
review_sources: ["CISCO_FMC_FTD_SECURITY_CATALOG.md", "MAIN_DEVICE_LINK_PORT_DISCOVERY.md"]
operational_boundary: "PROCEDURE_REVIEWED_LIVE_STATE_UNVERIFIED"
last_reviewed: "2026-08-16"
---

# Cisco Security Policy and Segmentation Evidence Triage

## Purpose

Use this procedure for an exact FMC or FTD entity when a reported network flow, segmentation boundary, access-control decision, or intrusion event requires diagnosis. The source catalog documents the management and enforcement roles, but it does not prove current device health, policy deployment, or traffic outcome.

## Evidence sequence

1. Fix the source, destination, protocol, port, service, exact target, and reported time window.
2. Separate FMC management-plane reachability from FTD data-plane enforcement.
3. Establish the relevant policy and deployment identity without assuming the latest documented policy is active.
4. Collect the smallest attributable access-control or intrusion observation for the exact flow.
5. Compare time-aligned adjacent routing and switching observations only when they belong to the same path.
6. Report supported, conflicting, and missing evidence separately.

## Decision boundaries

- FMC visibility does not prove FTD health or enforcement.
- A deployed rule does not prove it matched the reported flow.
- An intrusion or malware event does not prove it caused the user symptom.
- Missing evidence is `UNKNOWN`, never an inferred allow, block, or outage.

## Owner handoff

Return the exact entity, flow tuple, reported impact, evidence references, deployment identity when known, current reasoning state, and next bounded evidence objective. Read-only collection requires the owner to say `proceed`; policy changes, deployment, or remediation require a separate explicit owner instruction.
