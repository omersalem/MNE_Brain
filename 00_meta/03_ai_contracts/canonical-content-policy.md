# Canonical Content & Knowledge Governance Policy

## 1. Single Canonical Ownership
- Every infrastructure fact, device definition, and service procedure must have exactly ONE canonical document under `knowledge/`.
- Duplicate notes are strictly prohibited. Duplicates discovered by repository auditing must be mapped to a canonical file in `00_meta/03_governance/canonical-map.yaml` and archived/deleted.

## 2. Mandatory Metadata Frontmatter
Every canonical document in `knowledge/` must contain valid frontmatter:
```yaml
---
id: "fw-fortigate-hq-01"
type: "firewall"
aliases: ["FG-MNE", "FortiGate HQ"]
owner: "NetOps"
source: "Manual Audit"
trust_tier: 3
last_verified: "2026-07-27"
related_entities: ["sw-cisco-core-01", "vlan-100"]
---
```

## 3. Strict Truthfulness & Status Vocabulary
- AI agents and discovery scripts must NEVER emit `live_verified` status unless backed by actual, timestamped read-only adapter evidence in `operations/evidence/`.
- Permitted statuses are defined in `00_meta/03_ai_contracts/status-vocabulary.yaml`: `documented`, `live_verified`, `stale`, `unverified`, `failed`, `not_run`.
- Discovery scripts without adapter evidence must emit `not_run`.

## 4. Secret Protection Policy
- Plaintext passwords, private keys, authorization tokens, and credentials are strictly banned from Git-tracked files.
- Configuration profiles and runbooks must use environment variable references (`secret_ref: MNE_FORTIGATE_READONLY_CREDENTIAL`).
