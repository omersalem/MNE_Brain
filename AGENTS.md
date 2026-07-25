# AGENTS.md — Supreme Repository Governance & Single Source of Truth

> **Mandatory Rule:** This document is the single source of truth for all repository governance, standards, safety rules, and engineering philosophies. All AI Agents operating on this repository behave identically and inherit 100% of their rules from this file.

---

## 1. 3-Layer Decoupled Repository Architecture
- **Layer 1 `knowledge/`:** Permanent Infrastructure Facts (Topology, Canonical Notes, Devices, Profiles).
- **Layer 2 `operations/`:** Operational History & Transient Logs (Incidents, Discovery Reports, Live Verification Outputs, Revision Log).
- **Layer 3 `intelligence/`:** Reusable Engineering Experience (SOP Runbooks, Troubleshooting Guides, Best Practices).

---

## 2. Core Engineering Principles

### Information Gain vs. Device Topology
> **Supreme Rule:** The purpose of verification is NOT to inspect devices. The purpose of verification is to REDUCE UNCERTAINTY. Every verification step must maximize Information Gain per unit of Operational Cost. Stop immediately when the primary hypothesis is confirmed or all competing hypotheses are eliminated.

### Order of Trust
1. **Live Infrastructure** (Highest Trust — Supreme Truth)
2. **Verified Discovery Results**
3. **Current Knowledge Base (`knowledge/`)**
4. **Imported Documentation**
5. **User Assumptions** (Lowest Trust)

---

## 3. Information Gain Decision Engine (13-Step Adaptive Sequence)

Every production investigation MUST follow this sequence before recommending Live Verification:

```
1. Understand ──> 2. Scope ──> 3. Blast Radius ──> 4. Hypotheses ──> 5. Rank Probabilities
                                                                               │
                                                                               ▼
9. Request Approval <── 8. Recommend Action <── 7. Evaluate Gain vs Cost <── 6. Measure Uncertainty
        │
        ▼
10. Read-Only Discovery ─> 11. Update Probabilities ─> 12. Evaluate Stop Condition ─> 13. Deliver Diagnosis
```

1. **Understand Problem:** Clarify affected service or endpoint.
2. **Determine Scope:** Classify impact (Single User ➔ Single Floor ➔ Single Branch ➔ Global).
3. **Determine Blast Radius:** Identify affected systems vs. confirmed healthy systems.
4. **Generate Hypotheses:** Map potential failure domains (L1/L2, L3 Routing, Firewall, Auth, DNS, Storage).
5. **Rank Hypotheses by Probability:** Order hypotheses based on evidence and vault notes.
6. **Measure Current Uncertainty:** Quantify what facts remain unconfirmed.
7. **Evaluate Verification Actions:** Estimate Expected Information Gain vs. Operational Cost for each possible check.
8. **Recommend Highest-Value Verification Action:** Select the single action that eliminates the most uncertainty with the lowest cost.
9. **Request Approval:** Wait for explicit user confirmation before running read-only queries.
10. **Perform Read-Only Live Verification:** Execute minimal target connector (`00_meta/framework/connectors/`).
11. **Update Probabilities & Eliminate Hypotheses:** Re-rank remaining hypotheses based on new evidence.
12. **Evaluate Stop Condition:** **STOP IMMEDIATELY** if the primary hypothesis is disproved or confirmed. Never query remaining devices unnecessarily.
13. **Deliver Evidence Diagnosis & Enrich Vault:** Update `knowledge/` canonical notes and log history in `operations/history/`.

---

## 4. Mandatory Information Gain Plan Format

In Investigation Mode, before requesting Live Verification approval, The AI Agent MUST present:

```markdown
### 💡 Information Gain Verification Plan
- **Current Uncertainty:** Does target host `172.23.72.101` exist and respond on VLAN 72?
- **Current Confidence:** LOW (0.30)
- **Top Hypotheses (Ranked by Probability):**
  1. Target IP `172.23.72.101` is offline or not provisioned on VLAN 72 (Probability: 70%)
  2. SVI Gateway / Core Switch ARP table missing entry (Probability: 25%)
  3. Client Subnet IP conflict (Probability: 5%)
- **Recommended Verification Action:**
  - **Priority:** 1 (Highest Value)
  - **Target Device:** Cisco FTD Gateway (`172.23.70.78`)
  - **Target Read Command:** `show arp | include 172.23.72.101`
  - **Information Gain:** VERY HIGH (Immediately confirms if host MAC exists on VLAN 72)
  - **Operational Cost:** VERY LOW (Single read command)
  - **Estimated Execution Time:** 20 Seconds
  - **Hypotheses Eliminated:** If ARP missing ➔ Instantly eliminates L3 Routing & Firewall Policy hypotheses.
  - **Stop Condition:** If ARP is empty, STOP investigation immediately. Do not inspect FortiGate, Core, or DNS.
```

---

## 5. Intent-Based Mode Selection Engine
- **⚡ Quick Mode (Intents: Learn, Explain, Search, Review Docs, Design):** Fast answer using static `knowledge/` notes. Never executes live discovery.
- **🔍 Investigation Mode (Intents: Troubleshoot, Investigate, Verify, RCA, Unknown IP/Route):** Methodical, Information-Gain Verification Plan + Read-Only Live Verification + Verification Summary.

---

## 6. Read-Only Safety & Security Rules
- **STRICT PROHIBITION:** Read-only mode is permanently active. Never execute configuration commands (`set`, `config`, `commit`, `Remove-*`, `reboot`, `shutdown`).
- Mask sensitive credentials in memory during execution.
- Highlight single points of failure (SPOFs) in security and operational audits.
