---
runbook_id: "p5-identity-dns-triage"
title: "Identity and DNS Evidence Triage"
version: "1.0.0"
status: "operationally_reviewed"
runbook_type: "domain_troubleshooting"
scope_categories: ["identity"]
scope_services: ["active-directory", "dns", "primary-dns", "dns-replica", "kerberos", "ldap", "ldap-ssl", "ldap-replica"]
scope_entity_ids: ["dc-mne-ad-01", "dc-mne-ad-02", "dc-windows-ad-01", "dc-windows-ad-02"]
category_fallback_allowed: true
owner_team: "MNE-BRAIN-OWNER"
requires_exact_target: true
live_access_allowed: false
remediation_allowed: false
evidence_objectives: ["confirm-identity-symptom", "collect-dns-answer-state", "collect-domain-controller-reachability", "collect-directory-service-state", "collect-replication-state", "collect-time-dependency-state"]
stop_conditions: ["User, client, domain, or DNS name scope is unknown", "The owner has not explicitly said proceed for read-only collection", "Sensitive identity data would enter the handoff", "Replication or authentication evidence is stale, simulated, malformed, cross-target, or unattributable", "A directory, DNS, account, configuration, or remediation change is proposed without explicit owner instruction"]
source_basis: "owner_review"
review_sources: ["MASTER_ASSET_INVENTORY.md", "dns-fortigate-vpn.md"]
operational_boundary: "PROCEDURE_REVIEWED_LIVE_STATE_UNVERIFIED"
last_reviewed: "2026-08-16"
---

# Identity and DNS Evidence Triage

## Evidence sequence

1. Fix the exact controller or DNS service, affected client/service class, domain/name, and time window.
2. Separate client DNS configuration, answer state, time synchronization, controller reachability, directory services, and replication.
3. Minimize identity data and use opaque references for people and incidents.
4. Compare controllers only using attributable, time-aligned evidence.
5. Stop on conflicting controller results or before any directory, DNS, role, or account change.

## Decision boundaries

An authentication symptom does not prove an AD failure, and a DNS answer does not prove Kerberos or LDAP health. Conflicting controller observations require more evidence; they never authorize repair or role transfer.

## Owner handoff

Return the exact service scope, anonymized impact, evidence references, controller differences, unknowns, and next objective to `MNE-BRAIN-OWNER`. Never include passwords, tokens, personal attributes, or account secrets.
