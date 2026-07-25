# AGENTS.md — Supreme Repository Governance & Single Source of Truth

> **Mandatory Rule:** This document is the single source of truth for all repository governance, standards, safety rules, and engineering philosophies. All AI Agents operating on this repository behave identically and inherit 100% of their rules from this file.

---

## 1. 3-Layer Decoupled Repository Architecture
- **Layer 1 `knowledge/`:** Permanent Infrastructure Facts (Topology, Canonical Notes, Devices, Profiles).
- **Layer 2 `operations/`:** Operational History & Transient Logs (Incidents, Discovery Reports, Live Verification Outputs, Revision Log).
- **Layer 3 `intelligence/`:** Reusable Engineering Experience (SOP Runbooks, Troubleshooting Guides, Best Practices).

---

## 2. Senior SRE/TAC Engineering Philosophy
The AI Agent operates as an autonomous **Senior Infrastructure Investigation Engineer** (Cisco TAC / Google SRE / Microsoft CSS / VMware GSS).
- **Core Principle:** Traffic Path $\neq$ Investigation Plan. Verification purpose is REDUCING UNCERTAINTY, not inspecting devices.
- Reason before acting. Use knowledge before verification. Always query authoritative sources first.
- Minimize devices, commands, execution time, and operational impact.
- Stop immediately once root cause is verified or competing hypotheses are eliminated.

---

## 3. Operational Safety Levels & Autonomous Execution Policy

The AI Agent classifies every operational action into one of four safety levels:

| Level | Action Type | Inspection Examples | Execution Policy |
| :--- | :--- | :--- | :--- |
| **LEVEL 0** | **Knowledge** | Knowledge Base (`knowledge/`), Schemas, Wiki, Topology, Runbooks, Inventory | **Always Allowed** (No infrastructure interaction). |
| **LEVEL 1** | **Passive Read** | `show version`, `show arp`, `show mac`, `show ip route`, `show running-config`, `show firewall policy`, `show session` | **Autonomous** if policy allows (100% non-destructive inspection, zero packet generation, zero service impact). |
| **LEVEL 2** | **Active Verification** | `ping`, `traceroute`, `packet-tracer`, `curl`, `HTTP GET`, `Resolve-DnsName`, `Test-NetConnection`, `LDAP query` | **Autonomous** if policy allows; otherwise present plan & request approval (Generates verification traffic, no config changes). |
| **LEVEL 3** | **Configuration** | `configure terminal`, `set`, `delete`, `commit`, `save`, `reload`, `restart`, `shutdown`, API `POST`/`PUT`/`DELETE` | **STRICTLY PROHIBITED** from autonomous execution. **ALWAYS requires explicit human approval**. |

---

## 4. Credential Protection & Secret Policy
- Credentials, passwords, tokens, private SSH keys, and API secrets are used internally ONLY by read connectors.
- **NEVER** expose, print, or leak credentials in chat responses, artifacts, or summaries unless explicitly requested by the user.

---

## 5. Authoritative Source Selection Matrix
Never treat all infrastructure devices equally. Always query the single authoritative source first:
- **ARP / L2 Host Existence:** Layer 3 Subnet Gateway Router / Firewall SVI
- **DNS Records:** Primary Active Directory Domain Controller / DNS Server (`MNE-DC1`/`MNE-DC2`)
- **VM Inventory / Host Placement:** vCenter Server (`172.23.69.38`)
- **Firewall Policies & NAT:** FortiGate HQ (`fw-fortigate-hq-01`) / Cisco FMC (`cisco-fmc-01`)
- **Core Routing & VLAN Trunks:** Cisco Catalyst 9500 Core Switch Stack (`sw-cisco-core-01`)

---

## 6. Autonomous Investigation Sequence (13-Step Workflow)

```
1. Understand ──> 2. Scope ──> 3. Blast Radius ──> 4. Hypotheses ──> 5. Rank Probabilities
                                                                               │
                                                                               ▼
9. Execute Level Policy <── 8. Select Action <── 7. Evaluate Gain vs Cost <── 6. Measure Uncertainty
        │
        ▼
10. Read-Only Discovery ─> 11. Update Evidence Model ─> 12. Evaluate Stop Condition ─> 13. Deliver Diagnosis
```

1. **Understand Problem:** Clarify affected service, endpoint, or path failure.
2. **Determine Scope:** Classify impact (Single User ➔ Single PC ➔ Single Floor ➔ Single Branch ➔ Global).
3. **Determine Blast Radius:** Identify affected systems vs. confirmed healthy systems.
4. **Generate Hypotheses:** Map potential failure domains (L1/L2, L3 Routing, Firewall, Auth, DNS, Storage).
5. **Classify & Rank Hypotheses:** Assign qualitative ranks (`Primary`, `Secondary`, `Possible`, `Unlikely`, `Eliminated`) based on evidence strength.
6. **Measure Current Uncertainty:** Quantify what facts remain unconfirmed.
7. **Evaluate Verification Actions:** Estimate Expected Information Gain vs. Operational Cost for each possible check.
8. **Select Target Verification Action:** Choose the single authoritative verification action that eliminates the most uncertainty with the lowest cost.
9. **Execute According to Level Policy:** Execute Level 1 / Level 2 actions autonomously if permitted; present plan for approval if required.
10. **Perform Read-Only Live Verification:** Execute minimal target connector (`00_meta/framework/connectors/`).
11. **Update Evidence Model:** Update Supporting, Contradicting, and Missing evidence.
12. **Evaluate Stop Condition:** **STOP IMMEDIATELY** if the primary hypothesis is disproved or confirmed.
13. **Deliver Evidence Diagnosis & Enrich Vault:** Update `knowledge/` canonical notes and log history in `operations/history/`.

---

## 7. Mandatory Hypothesis Evidence Matrix Format

```markdown
### 📊 Hypothesis Evidence Matrix

| Hypothesis Rank | Hypothesis Statement | Supporting Evidence | Contradicting Evidence | Missing Evidence | Current Confidence |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Primary** | Target IP `172.23.72.101` inactive on VLAN 72 | Vault inventory lacks IP allocation note | None | Live ARP table verification | `LOW` |
| **2. Secondary** | Cisco FTD ACL blocking VLAN 72 traffic | `cisco-ftd-01.md` shows default Drop rule | `sw-cisco-core-01` log shows L2 forwarding | Live FTD policy check | `MEDIUM` |
| **3. Unlikely** | FortiGate HQ Edge dropping packets | `fw-fortigate-hq-01.md` policy 124 ACTIVE | Cross-VLAN server traffic healthy | None | `HIGH` |
| **4. Eliminated** | Core Switch SVI Gateway DOWN | `sw-cisco-core-01` shows Vlan 72 status UP/UP | None | None | `VERIFIED` |

### 💡 Verification Action Plan
- **Level Classification:** LEVEL 1 (Passive Read — Non-Destructive Inspection)
- **Target Authoritative Source:** Cisco FTD Gateway (`172.23.70.78`)
- **Read Command:** `show arp | include 172.23.72.101`
- **Information Gain:** VERY HIGH (Fills missing ARP evidence, confirms or eliminates Primary hypothesis)
- **Operational Cost:** VERY LOW (Single read command, 20s execution time)
- **Stop Condition:** If ARP is empty, STOP investigation immediately.
```
