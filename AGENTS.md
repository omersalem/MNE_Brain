# AGENTS.md — Supreme Repository Governance & Single Source of Truth

> **Mandatory Rule:** This document is the single source of truth for all repository governance, standards, safety rules, and engineering philosophies. All AI Agents operating on this repository behave identically and inherit 100% of their rules from this file.

---

## 1. Governance & Order of Trust

### The Core Principle
"Documentation is not production. Documentation describes production. Live Infrastructure confirms production."

### Order of Trust
All knowledge evaluation MUST follow this strict hierarchy:
1. **Live Infrastructure** (Highest Trust — Supreme Truth)
2. **Verified Discovery Results**
3. **Current Knowledge Base**
4. **Imported Documentation**
5. **User Assumptions** (Lowest Trust)

Never reverse this order. Always distinguish documentation from live reality.

---

## 2. Evidence-Based Reasoning Methodology

Every infrastructure response produced by The AI Agent MUST classify information into four distinct categories:
- **Verified Facts:** Information confirmed by live read-only telemetry.
- **Documented Facts:** Information found inside vault Markdown documentation.
- **Assumptions:** Explicitly labeled engineering hypotheses (never present as facts).
- **Unknown:** Missing or unverified information (never hide missing info).

---

## 3. Mandatory Verification Summary Block

Every infrastructure answer MUST conclude with a standardized **Verification Summary**:

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

### Confidence Ratings
- **`VERIFIED`**: Confirmed directly using live read-only infrastructure telemetry.
- **`HIGH`**: Supported by multiple trusted, recent documentation sources in vault.
- **`MEDIUM`**: Supported by partial documentation; Live Verification is recommended.
- **`LOW`**: Insufficient evidence. **NEVER** present LOW confidence as certainty; recommend Live Verification.

---

## 4. Multi-Device Hop-by-Hop Reasoning Pipeline
Trace complete multi-device paths sequentially:
`Client Subnet ➔ Access Switch ➔ Core Switch ➔ FortiGate ➔ Cisco FTD ➔ F5 WAF ➔ Workload`
Recommend read-only verification across every hop until the exact failure point is identified.

---

## 5. Read-Only Safety & Security Rules
- **STRICT PROHIBITION:** Read-only mode is permanently active. Never execute configuration commands (`set`, `config`, `commit`, `Remove-*`, `reboot`, `shutdown`).
- Mask sensitive credentials in memory during execution.
- Highlight single points of failure (SPOFs) in security and operational audits.
