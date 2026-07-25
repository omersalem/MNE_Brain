---
id: "MNE-STD-UCF-SPEC"
title: "Universal Discovery Connector Framework Specification"
type: "infrastructure_standard"
status: "active"
owner: "Senior-Software-Architect"
last_review: "2026-07-24"
tags:
  - ministry/standards/framework
---

# Universal Discovery Connector Framework Specification

Context: [[master-dashboard]] | Parent: [[index-standards]]

## 1. Overview & Architecture
The **Universal Discovery Connector Framework** is a vendor-neutral, modular Python software architecture designed to discover, validate, normalize, and enrich infrastructure knowledge across the Ministry Digital Twin.

All future vendor connectors (FortiGate, Cisco, F5, VMware, Active Directory, Exchange, Fujitsu SAN, Linux) inherit from a single abstract interface (`BaseConnector`) and execute a strict 11-stage discovery pipeline.

---

## 2. The 11-Stage Universal Pipeline

```
1. Connection Verification ──────> 2. Authentication Test ──────> 3. Capability Detection
                                                                           │
                                                                           ▼
6. Data Normalization <─────────── 5. Schema Validation <───────── 4. Data Collection
          │
          ▼
7. Relationship Auto-Detection ──> 8. Knowledge Comparison ──────> 9. Knowledge Enrichment
                                                                           │
                                                                           ▼
11. Discovery Reporting <───────── 10. Markdown Vault Update <──────────────┘
```

---

## 3. Core Safety Rules
1. **Read-Only Enforced:** All connectors operate in read-only mode. Write/configuration commands are forbidden.
2. **Prose Preservation:** Frontmatter fields and Wiki links are updated; human-authored prose is preserved.
3. **No Unconfirmed Credentials:** Connections rely on vault Connection Profiles (`00_meta/05_connections/`). Missing credentials require human input.
