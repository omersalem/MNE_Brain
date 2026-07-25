# AGENTS.md — Supreme Repository Governance & Single Source of Truth

> **Mandatory Rule:** This document is the single source of truth for all repository governance, standards, safety rules, and engineering philosophies. All AI Agents operating on this repository behave identically and inherit 100% of their rules from this file.

---

## 1. 3-Layer Decoupled Repository Architecture
- **Layer 1 `knowledge/`:** Permanent Infrastructure Facts (Topology, Canonical Notes, Devices, Profiles).
- **Layer 2 `operations/`:** Operational History & Transient Logs (Incidents, Discovery Reports, Live Verification Outputs, Revision Log).
- **Layer 3 `intelligence/`:** Reusable Engineering Experience (SOP Runbooks, Troubleshooting Guides, Best Practices).

---

## 2. Core Engineering Principles

### Traffic Path vs. Investigation Plan
> **Crucial Rule:** Traffic Path $\neq$ Investigation Plan. The traffic path describes how packets travel. The investigation plan describes the minimum work required to identify the root cause. Never confuse them. Senior engineers minimize investigation scope before inspecting devices.

### Order of Trust
1. **Live Infrastructure** (Highest Trust — Supreme Truth)
2. **Verified Discovery Results**
3. **Current Knowledge Base (`knowledge/`)**
4. **Imported Documentation**
5. **User Assumptions** (Lowest Trust)

---

## 3. Investigation Planning Engine (12-Step Sequence)

Every production investigation MUST follow this sequence before executing Live Verification:

```
1. Understand Problem ──> 2. Determine Scope ──> 3. Determine Blast Radius ──> 4. Generate Hypotheses
                                                                                       │
                                                                                       ▼
8. Request Approval <─── 7. Present Plan <─── 6. Select Minimum Devices <─── 5. Rank by Probability
        │
        ▼
9. Read-Only Discovery ─> 10. Update Hypotheses ─> 11. Pinpoint Root Cause ─> 12. Enrich Vault Knowledge
```

1. **Understand Problem:** Clarify affected service or endpoint.
2. **Determine Scope:** Classify impact (Single User ➔ Single PC ➔ Single Floor ➔ Single Branch ➔ Global).
3. **Determine Blast Radius:** Identify affected systems vs. confirmed healthy systems.
4. **Generate Hypotheses:** Map potential failure domains (L1/L2, L3 Routing, Firewall, Auth, DNS, Storage).
5. **Rank Hypotheses by Probability:** Order hypotheses based on evidence and scope. Do not treat all hypotheses equally.
6. **Select Minimum Devices Required:** Select the smallest possible set of devices required to confirm or eliminate top hypotheses. Never inspect devices unlikely to contribute to the diagnosis.
7. **Present Investigation Plan & Exclusions:** Explain why target devices were selected and why other path devices were excluded.
8. **Request Approval:** Wait for explicit user confirmation before running read-only queries.
9. **Perform Read-Only Live Verification:** Execute minimal target connectors (`00_meta/framework/connectors/`).
10. **Update Hypotheses & Exit Conditions:** Progressively eliminate non-causes based on success criteria.
11. **Pinpoint Root Cause:** Deliver evidence-based diagnosis.
12. **Enrich Vault Knowledge:** Update `knowledge/` canonical notes and promote reusable SOPs to `intelligence/runbooks/`.

---

## 4. Mandatory Pre-Verification Investigation Plan Format

In Investigation Mode, before requesting Live Verification approval, The AI Agent MUST present:

```markdown
### 📋 Investigation Plan
- **Investigation Scope:** Single User | Single Floor (VLAN 22) | Single Branch | Global
- **Blast Radius:** Affected: [Floor 2 Workstations] | Healthy: [Floors 1,3-6, Branches, Core Server Farm]
- **Current Confidence:** LOW (0.35)
- **Top Hypotheses (Ranked by Probability):**
  1. CoreSwitch1 VLAN 22 SVI Gateway / ARP resolution failure (Probability: 60%)
  2. Floor 2 Access Switch Port / Trunk VLAN tag mismatch (Probability: 30%)
  3. Client Subnet IP / DHCP Lease Conflict (Probability: 10%)
- **Excluded Hypotheses (With Reasoning):**
  - FortiGate HQ Edge (Excluded: External Internet & cross-VLAN servers healthy)
  - F5 WAF & Exchange DAG (Excluded: Core server farm healthy)
- **Minimum Devices Required:** CoreSwitch1 (`172.23.70.254`), Floor 2 Access Switch (`172.23.70.221`)
- **Success Criteria & Exit Conditions:** If `show ip arp vlan 22` on CoreSwitch1 resolves MAC ➔ Eliminate Layer 3, proceed to Access Switch port inspection.
```

---

## 5. Intent-Based Mode Selection Engine
- **⚡ Quick Mode (Intents: Learn, Explain, Search, Review Docs, Design):** Fast answer using static `knowledge/` notes. Never executes live discovery.
- **🔍 Investigation Mode (Intents: Troubleshoot, Investigate, Verify, RCA, Unknown IP/Route):** Methodical, minimum-device Investigation Plan + Read-Only Live Verification + Verification Summary.

---

## 6. Read-Only Safety & Security Rules
- **STRICT PROHIBITION:** Read-only mode is permanently active. Never execute configuration commands (`set`, `config`, `commit`, `Remove-*`, `reboot`, `shutdown`).
- Mask sensitive credentials in memory during execution.
- Highlight single points of failure (SPOFs) in security and operational audits.
