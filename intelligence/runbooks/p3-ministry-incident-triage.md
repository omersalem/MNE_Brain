---
runbook_id: "p3-ministry-incident-triage"
title: "P3 Ministry Incident Triage"
version: "1.1.0"
status: "operationally_reviewed"
runbook_type: "incident_process"
scope_categories: ["network", "compute", "storage", "identity", "messaging", "application"]
scope_services: []
scope_entity_ids: []
category_fallback_allowed: true
owner_team: "MNE-BRAIN-OWNER"
requires_exact_target: true
live_access_allowed: false
remediation_allowed: false
evidence_objectives: ["collect-target-reachability", "collect-dependency-state"]
stop_conditions: ["Target is unknown or ambiguous", "The owner has not explicitly said proceed for read-only collection", "Evidence is stale, simulated, malformed, or cross-target", "A write or remediation is proposed without explicit owner instruction"]
source_basis: "owner_review"
review_sources: ["AGENTS.md", "p3_troubleshooting_policy.yaml"]
operational_boundary: "PROCEDURE_REVIEWED_LIVE_STATE_UNVERIFIED"
last_reviewed: "2026-08-16"
---

# P3 Ministry Incident Triage Runbook

## Purpose

Use this runbook to turn a Ministry infrastructure symptom into a bounded, evidence-driven investigation without guessing current state or executing a change.

## Intake minimum

Record:

- affected hostname, canonical entity ID, service, IP, or branch;
- observed symptom and exact user impact;
- first known occurrence and whether impact is ongoing;
- reporter and affected location or population;
- any existing incident or change reference.

Do not continue with a target-dependent investigation if the orchestrator returns `CLARIFICATION_REQUIRED`.

## Offline triage sequence

1. Submit the symptom with one exact target.
2. Confirm the returned target identity and owner.
3. Treat every dependency entry as documented adjacency only.
4. Review `unknowns` before hypotheses or next checks.
5. Use the ordered `next_checks` as evidence objectives, not executable commands.
6. Unless `MNE-BRAIN-OWNER` explicitly says `proceed`, stop at `EVIDENCE_REQUIRED` and return the objectives to the owner.
7. If evidence later becomes available, require the complete P2 provenance envelope and re-run policy evaluation.
8. Accept a conclusion only when reasoning status is `EVIDENCE_SUPPORTED` and every cited evidence reference is attributable and fresh.
9. Treat `CONFLICTING_EVIDENCE` as a mandatory stop-and-collect-more-evidence state.

## Stop conditions

Stop immediately when:

- the target is unknown or ambiguous;
- a related entity is being treated as causal without evidence;
- the request would exceed the stated scope, time, output, or check budget;
- evidence is simulated, stale, malformed, cross-target, or lacks a P2 provenance envelope;
- a credential, raw command, or raw transport output appears in the handoff;
- a write, restart, failover, policy change, power action, or remediation is proposed.

## Handoff format

Provide the investigation ID, exact target, impact, accepted evidence references, remaining unknowns, ordered evidence objectives, current reasoning status, and owner-instruction blocker. Never label an offline result as verified production state.
