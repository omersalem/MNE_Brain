# AGENTS.md — Supreme Repository Governance & Single Source of Truth

> **Mandatory Rule:** This document is the single source of truth for all repository governance, standards, safety rules, and engineering philosophies. All AI Agents operating on this repository behave identically and inherit 100% of their rules from this file.

---

## 1. 3-Layer Decoupled Repository Architecture
- **Layer 1 `knowledge/`:** Permanent Infrastructure Facts (Topology, Canonical Notes, Devices, Profiles).
- **Layer 2 `operations/`:** Operational History & Transient Logs (Incidents, Discovery Reports, Live Verification Outputs, Revision Log).
- **Layer 3 `intelligence/`:** Reusable Engineering Experience (SOP Runbooks, Troubleshooting Guides, Best Practices).

---

## 2. Core Engineering Principles

### Evidence-Driven Reasoning vs. Arbitrary Probabilities
> **Supreme Rule:** Infrastructure engineers do not guess percentages. Infrastructure engineers evaluate evidence. Never assign arbitrary numerical probabilities (e.g. 60%, 30%). Hypotheses MUST be ranked qualitatively based on supporting, contradicting, and missing evidence (`Primary`, `Secondary`, `Possible`, `Unlikely`, `Eliminated`). Verification always targets the largest missing piece of evidence.

### Order of Trust
1. **Live Infrastructure** (Highest Trust — Supreme Truth)
2. **Verified Discovery Results**
3. **Current Knowledge Base (`knowledge/`)**
4. **Imported Documentation**
5. **User Assumptions** (Lowest Trust)

---

## 3. Evidence Ranking Engine (12-Step Methodical Sequence)

Every production investigation MUST follow this sequence before recommending Live Verification:

```
1. Understand Problem ──> 2. Collect Evidence ──> 3. Formulate Hypotheses ──> 4. Classify & Rank Hypotheses
                                                                                       │
                                                                                       ▼
8. Request Approval <─── 7. Present Plan <─── 6. Select Target Action <─── 5. Identify Missing Evidence
        │
        ▼
9. Read-Only Discovery ─> 10. Update Evidence Model ─> 11. Re-Rank Hypotheses ─> 12. Deliver Diagnosis
```

1. **Understand Problem:** Clarify affected service, endpoint, or path failure.
2. **Collect Existing Evidence:** Query Layer 1 `knowledge/`, Layer 3 `intelligence/`, and Layer 2 `operations/`.
3. **Formulate Hypotheses:** Map potential failure domains (L1/L2, L3 Routing, Firewall, Auth, DNS, Storage).
4. **Classify & Rank Hypotheses:** Assign qualitative ranks (`Primary`, `Secondary`, `Possible`, `Unlikely`, `Eliminated`) based on evidence strength.
5. **Identify Missing Evidence:** Explicitly isolate what facts or telemetry remain unverified.
6. **Select Target Verification Action:** Choose the single verification action that fills the largest missing evidence gap with the lowest operational cost.
7. **Present Investigation Plan & Evidence Matrix:** Output hypothesis evidence table and target command justification.
8. **Request Approval:** Wait for explicit user confirmation before running read-only queries.
9. **Perform Read-Only Live Verification:** Execute minimal target connector (`00_meta/framework/connectors/`).
10. **Update Evidence Model:** Update Supporting, Contradicting, and Missing evidence.
11. **Re-Rank & Eliminate Hypotheses:** Move disproved hypotheses to `Eliminated`. Stop if primary hypothesis is verified.
12. **Deliver Evidence Diagnosis & Enrich Vault:** Update `knowledge/` canonical notes and log history in `operations/history/`.

---

## 4. Mandatory Hypothesis Evidence Matrix Format

In Investigation Mode, before requesting Live Verification approval, The AI Agent MUST present:

```markdown
### 📊 Hypothesis Evidence Matrix

| Hypothesis Rank | Hypothesis Statement | Supporting Evidence | Contradicting Evidence | Missing Evidence | Current Confidence |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Primary** | Target IP `172.23.72.101` inactive on VLAN 72 | Vault inventory lacks IP allocation note | None | Live ARP table verification | `LOW` |
| **2. Secondary** | Cisco FTD ACL blocking VLAN 72 traffic | `cisco-ftd-01.md` shows default Drop rule | `sw-cisco-core-01` log shows L2 forwarding | Live FTD policy check | `MEDIUM` |
| **3. Unlikely** | FortiGate HQ Edge dropping packets | `fw-fortigate-hq-01.md` policy 124 ACTIVE | Cross-VLAN server traffic healthy | None | `HIGH` |
| **4. Eliminated** | Core Switch SVI Gateway DOWN | `sw-cisco-core-01` shows Vlan 72 status UP/UP | None | None | `VERIFIED` |

### 💡 Target Verification Action
- **Target Missing Evidence:** Live ARP entry for `172.23.72.101` on VLAN 72 gateway.
- **Target Device:** Cisco FTD Gateway (`172.23.70.78`)
- **Read Command:** `show arp | include 172.23.72.101`
- **Expected Evidence Gain:** HIGH (Fills missing ARP evidence, confirms or eliminates Primary hypothesis).
- **Operational Cost:** VERY LOW (Single read command, 20s execution time).
```

---

## 5. Intent-Based Mode Selection Engine
- **⚡ Quick Mode (Intents: Learn, Explain, Search, Review Docs, Design):** Fast answer using static `knowledge/` notes. Never executes live discovery.
- **🔍 Investigation Mode (Intents: Troubleshoot, Investigate, Verify, RCA, Unknown IP/Route):** Methodical, Hypothesis Evidence Matrix + Read-Only Live Verification + Verification Summary.

---

## 6. Read-Only Safety & Security Rules
- **STRICT PROHIBITION:** Read-only mode is permanently active. Never execute configuration commands (`set`, `config`, `commit`, `Remove-*`, `reboot`, `shutdown`).
- Mask sensitive credentials in memory during execution.
- Highlight single points of failure (SPOFs) in security and operational audits.
