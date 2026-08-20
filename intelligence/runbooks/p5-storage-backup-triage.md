---
runbook_id: "p5-storage-backup-triage"
title: "Storage and Backup Evidence Triage"
version: "1.0.0"
status: "operationally_reviewed"
runbook_type: "domain_troubleshooting"
scope_categories: ["storage"]
scope_services: ["san-storage", "san-lun-management", "iscsi", "iscsi-target", "fibre-channel", "veeam-backup", "vm-snapshots", "san-repository", "disaster-recovery"]
scope_entity_ids: ["backup-veeam-hq-01", "san-fujitsu-01", "san-greenunit-01"]
category_fallback_allowed: true
owner_team: "MNE-BRAIN-OWNER"
requires_exact_target: true
live_access_allowed: false
remediation_allowed: false
evidence_objectives: ["confirm-storage-or-job-scope", "collect-target-reachability", "collect-capacity-state", "collect-path-state", "collect-job-state", "collect-repository-state", "collect-virtualization-dependency-state"]
stop_conditions: ["Affected volume, path, repository, job, or workload is unknown", "The owner has not explicitly said proceed for read-only collection", "Capacity, path, and backup symptoms are conflated", "Evidence is stale, simulated, malformed, or cross-target", "A LUN, snapshot, retention, rescan, restore, configuration, or remediation action is proposed without explicit owner instruction"]
source_basis: "owner_review"
review_sources: ["STORAGE_AND_BACKUP_BASELINE.md", "VEEAM_BACKUP_PLATFORM_BASELINE.md"]
operational_boundary: "PROCEDURE_REVIEWED_LIVE_STATE_UNVERIFIED"
last_reviewed: "2026-08-16"
---

# Storage and Backup Evidence Triage

## Evidence sequence

1. Fix the exact array, repository, job, path, or protected workload and the reported time window.
2. Separate management reachability, capacity, FC/iSCSI path, repository, job, snapshot, and workload state.
3. Correlate backup and storage observations only when they reference the same workload and window.
4. Record successful and failed observations without inferring root cause.
5. Stop before restore, rescan, retention, snapshot, path, LUN, or configuration actions.

## Decision boundaries

A job failure does not prove a storage fault, a reachable array does not prove application I/O health, and available capacity does not prove path or repository health.

## Owner handoff

Return exact target/workload, protected scope, evidence references, dependency unknowns, and next objective to `MNE-BRAIN-OWNER`. Restore and storage changes always require a separate explicit instruction.
