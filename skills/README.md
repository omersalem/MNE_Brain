# Ministry Infrastructure Brain — Project Skills Directory

## Overview
This directory contains the four core project-specific Skills for the Ministry Infrastructure Brain. Live Verification is embedded as an automatic core capability within **every Skill**.

The AI Agent never requires explicit requests to verify infrastructure; it automatically evaluates confidence (`VERIFIED`, `HIGH`, `MEDIUM`, `LOW`) and recommends read-only Live Verification whenever documentation is incomplete.

---

## 🛠️ The 4 Embedded-Verification Project Skills

```
                                  ┌───────────────────────────────┐
                                  │           AGENTS.md           │
                                  │ (Order of Trust & Goverance)  │
                                  └───────────────┬───────────────┘
                                                  │
                                                  ▼
                                  ┌───────────────────────────────┐
                                  │      skills/ (4 Core Skills)  │
                                  └───────────────┬───────────────┘
                                                  │
         ┌─────────────────┬──────────────────────┴──────────────────────┬─────────────────┐
         ▼                 ▼                                             ▼                 ▼
    discover/           search/                                       explain/          review/
 (Import & Enrich)   (Deep Vault Search)                            (Path Topology)  (Quality Audit)
         │                 │                                             │                 │
         └─────────────────┴─────────────┬───────────────────────────────┴─────────────────┘
                                         │
                                         ▼
                         ┌───────────────────────────────┐
                         │ Embedded Live Verification    │
                         │ (Read-Only Telemetry Engine)  │
                         └───────────────────────────────┘
```

| Skill Name | Path | Purpose | Embedded Live Verification Triggers |
| :--- | :--- | :--- | :--- |
| **`discover`** | `skills/discover/skill.md` | Ingest, enrich, and update Digital Twin | Triggers Live Verification when imported docs leave unverified IP/route gaps. |
| **`search`** | `skills/search/skill.md` | Deep vault search & index traversal | Triggers Live Verification when queried objects (IP, MAC, VM, VLAN) are missing. |
| **`explain`** | `skills/explain/skill.md` | Explain path topology & dependencies | Triggers Live Verification when path hops cannot be confirmed from static notes. |
| **`review`** | `skills/review/skill.md` | Vault health, SPOF, & link review | Triggers Live Verification to resolve conflicting documentation or broken links. |

---

## 🔄 Automatic Decision-Making Workflow Across All Skills

Every Skill executes the following decision pipeline automatically:

```
Search Vault Knowledge ──> Evaluate Confidence ──> Assess Docs Sufficiency ──> Check Available Connectors ──> Recommend Read-Only Live Verification ──> Request Approval ──> Execute Discovery ──> Enrich Vault ──> Final Answer
```
