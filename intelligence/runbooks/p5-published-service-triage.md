---
runbook_id: "p5-published-service-triage"
title: "Published Web Service Evidence Triage"
version: "1.0.0"
status: "operationally_reviewed"
runbook_type: "domain_troubleshooting"
scope_categories: ["network", "compute", "application"]
scope_services: ["waf-protection", "load-balancing", "ssl-offloading", "asm-policy", "nginx-80", "http-80", "internal-portal", "auction-portal", "apdct-service"]
scope_entity_ids: ["waf-f5-bigip-01", "app-apdct-web-01", "app-auction-test-01", "web-greenunit-ubuntu-01"]
category_fallback_allowed: false
owner_team: "MNE-BRAIN-OWNER"
requires_exact_target: true
live_access_allowed: false
remediation_allowed: false
evidence_objectives: ["confirm-public-symptom", "collect-name-resolution-state", "collect-virtual-service-state", "collect-pool-member-state", "collect-backend-service-state", "collect-security-event-state"]
stop_conditions: ["Hostname or application target is unknown", "Public and internal observations are not separated", "The owner has not explicitly said proceed for read-only collection", "Certificate, WAF, or backend evidence is stale, simulated, malformed, or cross-target", "A DNS, WAF, pool, backend, configuration, or remediation change is proposed without explicit owner instruction"]
source_basis: "owner_review"
review_sources: ["MNE_INFRASTRUCTURE_MASTER_GUIDE.md", "f5-bigip-publishing.md", "dns-fortigate-vpn.md"]
operational_boundary: "PROCEDURE_REVIEWED_LIVE_STATE_UNVERIFIED"
last_reviewed: "2026-08-16"
---

# Published Web Service Evidence Triage

## Evidence sequence

1. Fix the hostname, URI or service path, client perspective, exact F5/backend entity, and time window.
2. Separate DNS, client reachability, virtual server, TLS, WAF decision, pool member, and backend application layers.
3. Collect the smallest time-aligned observation at the first unknown layer.
4. Correlate WAF and backend evidence only by the same request window and service path.
5. Stop before DNS, virtual-server, pool, certificate, WAF, or backend changes.

## Decision boundaries

An HTTP symptom does not identify the failed layer. A healthy pool member does not prove the application response, a WAF event does not prove causality, and documented publication relationships remain context until freshly observed.

## Owner handoff

Return exact hostname/path, perspectives tested, accepted evidence, conflicting results, remaining unknowns, and the next objective to `MNE-BRAIN-OWNER`. The system sends no notification and performs no assignment.
