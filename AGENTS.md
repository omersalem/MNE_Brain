# AGENTS.md — Supreme Repository Governance & Single Source of Truth

> **Mandatory Rule:** This document is the single source of truth for all repository governance, standards, safety rules, and engineering philosophies. All AI Agents operating on this repository behave identically and inherit 100% of their rules from this file.

---

## 1. 3-Layer Decoupled Repository Architecture
- **Layer 1 `knowledge/`:** Permanent Infrastructure Facts (Topology, Canonical Notes, Devices, Profiles).
- **Layer 2 `operations/`:** Operational History & Transient Logs (Incidents, Discovery Reports, Live Verification Outputs, Revision Log).
- **Layer 3 `intelligence/`:** Reusable Engineering Experience (SOP Runbooks, Troubleshooting Guides, Best Practices).

---

## 2. Core Engineering Philosophy & Language Rules

### Observation vs. Interpretation vs. Conclusion
> **Supreme Rule:** Observations are facts. Interpretations are hypotheses. Conclusions require sufficient evidence. Never confuse these three concepts. The AI Agent MUST NEVER jump directly from Observation to Conclusion without executing Verification.

```
Observation (Fact) ──> Interpretation (Hypothesis) ──> Required Verification ──> Conclusion (Verified Decision)
```

### Language Precision Standards
- **PROHIBITED:** Absolute statements before live verification (e.g., *"The host is offline"*, *"The firewall is blocking traffic"*).
- **MANDATORY:** Qualified engineering language (e.g., *"The current evidence indicates no ARP entry exists on VLAN 72 gateway; this suggests the host may be inactive, but verification via vCenter/ping is required."*).

---

## 3. Blast Radius & Scope Classification
Never assume unverified systems are healthy:
- **Known Affected:** Verified impacted systems (`Floor 2 Workstations`).
- **Known Healthy:** Confirmed healthy ONLY if verified via telemetry.
- **Unknown:** Systems without verified telemetry (`Floor 1`, `Branches`, `VPN`, `Internet Edge`).

---

## 4. Operational Safety Levels & Execution Policy

| Level | Action Type | Inspection Examples | Execution Policy |
| :--- | :--- | :--- | :--- |
| **LEVEL 0** | **Knowledge** | Knowledge Base (`knowledge/`), Schemas, Wiki, Topology, Runbooks, Inventory | **Always Allowed** (No infrastructure interaction). |
| **LEVEL 1** | **Passive Read** | `show version`, `show arp`, `show mac`, `show ip route`, `show running-config`, `show firewall policy`, `show session` | **Autonomous** if policy allows (100% non-destructive inspection, zero packet generation, zero service impact). |
| **LEVEL 2** | **Active Verification** | `ping`, `traceroute`, `packet-tracer`, `curl`, `HTTP GET`, `Resolve-DnsName`, `Test-NetConnection`, `LDAP query` | **Autonomous** if policy allows; otherwise present plan & request approval (Generates verification traffic, no config changes). |
| **LEVEL 3** | **Configuration** | `configure terminal`, `set`, `delete`, `commit`, `save`, `reload`, `restart`, `shutdown`, API `POST`/`PUT`/`DELETE` | **STRICTLY PROHIBITED** from autonomous execution. **ALWAYS requires explicit human approval**. |

---

## 5. Credential Protection & Secret Policy
- Credentials, passwords, tokens, private SSH keys, and API secrets are used internally ONLY by read connectors.
- **NEVER** expose, print, or leak credentials in chat responses, artifacts, or summaries unless explicitly requested by the user.

---

## 6. Investigation & Verification Framework (Mandatory Format)

In Investigation Mode, The AI Agent MUST structure investigation outputs into the **Observation-Interpretation Matrix**:

```markdown
### 🔬 Observation, Interpretation & Conclusion Matrix

- **1. Directly Observed Facts (Observations):**
  - No ARP entry for `172.23.72.101` on VLAN 72 gateway (`sw-cisco-core-01`).
  - Core switch VLAN 72 SVI interface is status `UP/UP`.

- **2. Engineering Interpretations (Hypotheses):**
  - *Primary:* Target host `172.23.72.101` is powered off or disconnected from switch port.
  - *Secondary:* Host interface is configured with an incorrect IP subnet.
  - *Unlikely:* ARP cache timeout (no broadcast traffic observed).

- **3. Blast Radius Categorization:**
  - *Known Affected:* Workstation `172.23.72.101`
  - *Known Healthy:* Gateway SVI `172.23.72.1` (`VERIFIED`)
  - *Unknown:* Other VLAN 72 endpoints, Floor 2 access switch ports

- **4. Required Verification Plan (Level 1 / Level 2):**
  - **Target Device:** vCenter Appliance (`172.23.69.38`) / Access Switch (`172.23.70.221`)
  - **Read Command:** `Get-VM -Name "WORKSTATION-101"` / `show mac address-table interface gi1/0/12`
  - **Expected Evidence Gain:** HIGH (Fills missing VM power state / MAC learning evidence)
  - **Stop Condition:** If VM power state is `PoweredOff`, STOP investigation immediately.

- **5. Conclusion:**
  - *Status:* UNVERIFIED (Awaiting read-only verification). No final conclusion produced prior to evidence collection.
```

---

## 7. Intent-Based Mode Selection Engine
- **⚡ Quick Mode (Intents: Learn, Explain, Search, Review Docs, Design):** Fast answer using static `knowledge/` notes. Never executes live discovery.
- **🔍 Investigation Mode (Intents: Troubleshoot, Investigate, Verify, RCA, Unknown IP/Route):** Methodical Observation-Interpretation Framework + Read-Only Live Verification + Verification Summary.
