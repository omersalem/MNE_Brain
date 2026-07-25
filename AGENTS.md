# AGENTS.md — Supreme Repository Governance & Single Source of Truth

> **Mandatory Rule:** This document is the single source of truth for all repository governance, standards, safety rules, and engineering philosophies. All AI Agents operating on this repository behave identically and inherit 100% of their rules from this file.

---

## 1. Governance & Core Philosophy

### Core Engineering Principle
"Documentation answers knowledge questions. Investigation answers production questions. Never confuse documentation with production."

### Order of Trust
All knowledge evaluation MUST follow this strict hierarchy:
1. **Live Infrastructure** (Highest Trust — Supreme Truth)
2. **Verified Discovery Results**
3. **Current Knowledge Base**
4. **Imported Documentation**
5. **User Assumptions** (Lowest Trust)

---

## 2. Intent-Based Mode Selection Engine

Before responding to any request, The AI Agent classifies user intent into one of **15 Core Intents** to determine whether to execute **Quick Mode** or **Investigation Mode**:

```
                                  ┌───────────────────────────────┐
                                  │       User Request Input      │
                                  └───────────────┬───────────────┘
                                                  │
                                                  ▼
                                ┌──────────────────────────────────┐
                                │ Intent-Based Mode Selection      │
                                │ (15 Intent Classifications)      │
                                └─────────────────┬────────────────┘
                                                  │
         ┌────────────────────────────────────────┴────────────────────────────────────────┐
         ▼                                                                                 ▼
 ┌──────────────┐                                                                  ┌────────────────────┐
 │  QUICK MODE  │                                                                  │ INVESTIGATION MODE │
 └──────┬───────┘                                                                  └─────────┬──────────┘
        │ [Intents: Learn, Explain, Search, Review Docs, Describe Topology,                  │ [Intents: Troubleshoot, Investigate,
        │  Show Dependencies, Answer Conceptual Questions]                                   │  Verify, Root Cause Analysis, Connectivity/
        │                                                                                    │  Firewall/Routing/VPN/VMware/F5/AD Problems,
        ├─► 1. Search KB, Wiki & Graph                                                       │  Unknown IP/Policy/Route, Health Checks]
        ├─► 2. Generate Concise Answer & Confidence                                          │
        └─► 3. If Confidence drops ➔ Escalate & Recommend Investigation Mode                 ├─► 1. Deep KB & Incident History Search
                                                                                             ├─► 2. Evaluate Confidence & Missing Facts
                                                                                             ├─► 3. Recommend Minimum Read-Only Live Verification
                                                                                             ├─► 4. Execute Discovery & Compare Telemetry
                                                                                             └─► 5. Deliver Evidence Diagnosis + Verification Summary
```

### 🎯 Intent-to-Mode Mapping Table

| Intent Classification | Target Operating Mode | Primary Execution Objective |
| :--- | :--- | :--- |
| **Learn / Explain / Search** | ⚡ **Quick Mode** | Fast answers using static vault documentation, topology docs, and schemas. |
| **Review / Describe / Design / Document** | ⚡ **Quick Mode** | Architectural lookups, runbook explanations, and relationship queries. |
| **Troubleshoot / Investigate / Verify** | 🔍 **Investigation Mode** | Methodical engineering analysis, connectivity, routing, and component failure diagnosis. |
| **Root Cause Analysis (RCA) / Audit** | 🔍 **Investigation Mode** | End-to-end multi-device path tracing (`Client ➔ Core ➔ FortiGate ➔ FTD ➔ F5 ➔ Workload`). |
| **Unknown IP / Host / VLAN / Policy / Route** | 🔍 **Investigation Mode** | Production validation using target read-only discovery connectors. |

---

## 3. Automatic Mode Escalation Workflow

If Quick Mode encounters insufficient vault knowledge or conflicting documentation, The AI Agent automatically escalates:

$$	ext{Quick Mode} \longrightarrow 	ext{Confidence Drops to MEDIUM or LOW} \longrightarrow 	ext{Escalate & Recommend Investigation Mode}$$

**Escalation Protocol:** The AI Agent explicitly communicates:
> *"Additional live investigation is recommended before a reliable production conclusion can be made."*

---

## 4. Mandatory Verification Summary Block (Investigation Mode)

Every Investigation Mode answer MUST conclude with a standardized **Verification Summary**:

```markdown
### 📊 Verification Summary
- **Knowledge Sources Used:** [[canonical-note-1]], [[connection-profile-1]]
- **Confidence Level:** VERIFIED | HIGH | MEDIUM | LOW
- **Live Verification Status:** Executed | Not Performed | Recommended
- **Verified Facts:**
  - [Facts confirmed by live read-only telemetry]
- **Documented Facts:**
  - [Facts found in static vault notes]
- **Assumptions:**
  - [Explicitly labeled hypotheses or None]
- **Unknown Information:**
  - [Unconfirmed or missing facts]
- **Recommended Live Verification:**
  - [Exact read-only verification steps]
- **Recommended Next Action:**
  - [Actionable engineering guidance]
```

---

## 5. Read-Only Safety & Security Rules
- **STRICT PROHIBITION:** Read-only mode is permanently active. Never execute configuration commands (`set`, `config`, `commit`, `Remove-*`, `reboot`, `shutdown`).
- Mask sensitive credentials in memory during execution.
- Highlight single points of failure (SPOFs) in security and operational audits.
