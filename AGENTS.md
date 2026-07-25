# AGENTS.md — Supreme Repository Governance & Single Source of Truth

> **Mandatory Rule:** This document is the single source of truth for all repository governance, standards, safety rules, and engineering philosophies. All AI Agents operating on this repository behave identically and inherit 100% of their rules from this file.

---

## 1. 3-Layer Decoupled Repository Architecture

The repository is strictly partitioned into three logical layers to separate permanent facts from operational logs and reusable experience:

```
+-----------------------------------------------------------------------------------+
|                        3-LAYER DECOUPLED BRAIN ARCHITECTURE                       |
+-----------------------------------------------------------------------------------+
| LAYER 1: knowledge/ (Permanent Infrastructure Facts)                              |
| - Architecture, Network Topology, Devices, FortiGate, Cisco, F5, AD, Exchange,    |
|   VMware, Fujitsu SAN, Linux, VLANs, Services, Connection Profiles.               |
+-----------------------------------------------------------------------------------+
                                      │
                                      ▼
+-----------------------------------------------------------------------------------+
| LAYER 2: operations/ (Operational History & Transient Logs)                       |
| - Incidents (`operations/incidents/`), Discovery Sessions (`operations/discovery/`),|
|   Live Verification Results (`operations/live-verification/`), Revision History.  |
| - Rule: Nothing in this layer is treated as permanent infrastructure facts.      |
+-----------------------------------------------------------------------------------+
                                      │
                                      ▼
+-----------------------------------------------------------------------------------+
| LAYER 3: intelligence/ (Reusable Engineering Experience)                          |
| - SOP Runbooks (`intelligence/runbooks/`), Troubleshooting Guides (`troubleshooting/`),|
|   Lessons Learned, Best Practices, Known Issues, Architectural Patterns.          |
| - Rule: Only verified, stable, and reusable operational experience exists here.    |
+-----------------------------------------------------------------------------------+
```

---

## 2. Layered Search Strategy by User Intent

The AI Agent must NOT search all directories equally. It routes query retrieval sequentially through layers based on the classified user intent:

- **Explain / Design / Learn Intent:** `knowledge/` ➔ `intelligence/`
- **Search / Lookup Intent:** `knowledge/` ➔ `intelligence/` ➔ `operations/` *(only if required)*
- **Review / Audit Intent:** `knowledge/` ➔ `operations/` ➔ `intelligence/`
- **Discover / Ingest Intent:** `knowledge/` ➔ Live Infrastructure
- **Troubleshoot / Investigate Intent:** `knowledge/` ➔ `operations/` ➔ Read-Only Live Verification ➔ `intelligence/`

---

## 3. Knowledge Promotion Protocol

Operational history (`operations/`) MUST NEVER automatically become permanent knowledge (`knowledge/`) or reusable engineering experience (`intelligence/`).

**Promotion Criteria:** Information is promoted into `knowledge/` or `intelligence/` ONLY when it is:
1. **Verified:** Confirmed via live read-only telemetry.
2. **Stable:** Confirmed non-transient across multiple observations.
3. **Reusable & Long-term:** Provides value for future engineering operations.

---

## 4. Evidence-Based Reasoning & Verification Summary

### Information Classification
- **Verified Facts:** Telemetry confirmed directly via live read-only inspection.
- **Documented Facts:** Facts found inside `knowledge/` notes.
- **Assumptions:** Explicitly labeled hypotheses (never present as facts).
- **Unknown:** Missing or unverified information (never hide missing info).

### Mandatory Verification Summary Block
Every Investigation Mode answer MUST conclude with:

```markdown
### 📊 Verification Summary
- **Knowledge Sources Used:** [[knowledge/path/note]], [[connection-profile]]
- **Confidence Level:** VERIFIED | HIGH | MEDIUM | LOW
- **Live Verification Status:** Executed | Not Performed | Recommended
- **Verified Facts:**
  - [Live confirmed facts]
- **Documented Facts:**
  - [Vault knowledge facts]
- **Assumptions:**
  - [Explicit hypotheses or None]
- **Unknown Information:**
  - [Missing parameters]
- **Recommended Live Verification:**
  - [Target read-only queries]
- **Recommended Next Action:**
  - [Actionable guidance]
```

---

## 5. Read-Only Safety & Security Rules
- **STRICT PROHIBITION:** Read-only mode is permanently active. Never execute configuration commands (`set`, `config`, `commit`, `Remove-*`, `reboot`, `shutdown`).
- Mask sensitive credentials in memory during execution.
- Highlight single points of failure (SPOFs) in security and operational audits.
