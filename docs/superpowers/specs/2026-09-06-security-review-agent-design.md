# MNE Security Review & Reporting Agent — Architecture & Design Specification

- **Date:** 2026-09-06
- **Status:** Approved / Ready for Implementation Planning
- **Author:** Antigravity (Pair Programming with MNE Owner)
- **Target Subsystem:** `core/security_review/` & `core/connectors/security/`

---

## 1. Executive Summary & Objective

The **MNE Security Review & Reporting Agent** is an automated, resilient cybersecurity intelligence subsystem integrated into `MNE_Brain_v2`. It connects to the Ministry of National Economy's core perimeter and identity infrastructure on a daily schedule, collects and normalizes security logs from the past 24 hours, correlates multi-vector threats, classifies incidents into standardized severity tiers (**Critical**, **High**, **Medium**), and dispatches an executive-level **HTML email** and matching **PDF report** every morning at **07:00 AM** to designated administrators.

For every Critical and High risk, the agent generates concrete, copy-pasteable CLI commands and step-by-step GUI instructions for immediate containment and root-cause resolution. In addition, it supports **Mode B (Controlled On-Demand Execution)**, allowing authorized administrators to command MNE_Brain to execute verified mitigations safely.

---

## 2. Target Perimeter & Scope of Devices

| Device | Role | IP / Host | Primary Protocols | Key Security Events Collected |
| :--- | :--- | :--- | :--- | :--- |
| **FortiGate** | Edge Firewall & SSL-VPN | `172.23.70.4` | REST API (`/api/v2/log/`) / SSH CLI | IPS attacks, Antivirus/malware detections, SSL-VPN failed/brute-force logins, configuration changes |
| **F5 BIG-IP** | WAF & Load Balancing | `172.23.70.89` | SSH (`/var/log/asm`, `tmsh`) / iControl REST | WAF/ASM security violations (SQLi, XSS, bot scrapers), virtual server/pool health failures, SSL certificate expiry alerts |
| **Cisco FMC / FTD** | Internal IPS & Firepower | `172.23.70.77` / `.78` | FMC REST API / FTD SSH | Snort intrusion events, Security Intelligence malicious IP blocks, malware file detections |
| **Sophos Email** | Email Protection Appliance | `172.23.71.39:4444` | HTTPS WebConsole / XML API / SSH | SMTP quarantine spikes, Zero-day / Sandstorm detonations, high-confidence phishing, spoofing/DKIM violations |
| **Active Directory** | Domain Controller (MNE-DC1)| `172.23.71.27` | WinRM / PowerShell Remoting | Event 4625 (failed logons), Event 4740 (account lockouts), Event 4728/4732/4756 (Domain/Enterprise Admin group changes) |
| **Exchange 2019** | Mail Server | `172.23.71.36` | WinRM / PowerShell Remoting | Message tracking anomalies, open-relay probe attempts, external authentication failures |

---

## 3. End-to-End Pipeline Architecture

```
                                  07:00 AM Daily Trigger
                                            │
                                            ▼
                    ┌──────────────────────────────────────────────┐
                    │    1. Ingestion Pipeline (Fault-Isolated)    │
                    ├──────────────────────────────────────────────┤
                    │ • FortiGate Collector    • F5 WAF Collector  │
                    │ • Cisco FMC Collector    • Sophos Collector  │
                    │ • AD Security Collector  • Exchange Collector│
                    └───────────────────────┬──────────────────────┘
                                            │
                                            ▼
                    ┌──────────────────────────────────────────────┐
                    │    2. Normalization & Correlation Engine     │
                    ├──────────────────────────────────────────────┤
                    │ • Unified Common Threat Schema               │
                    │ • Deduplication & Volume Aggregation         │
                    │ • Cross-Device Multi-Vector Correlation      │
                    │ • Severity Scoring (Critical / High / Med)   │
                    └───────────────────────┬──────────────────────┘
                                            │
                                            ▼
                    ┌──────────────────────────────────────────────┐
                    │    3. Remediation Intelligence Matcher       │
                    ├──────────────────────────────────────────────┤
                    │ • Step-by-Step Device CLI & GUI Playbooks    │
                    │ • Immediate Containment vs Permanent Fix     │
                    │ • Mode B Assisted Remediation Trigger Tokens  │
                    └───────────────────────┬──────────────────────┘
                                            │
                                            ▼
                    ┌──────────────────────────────────────────────┐
                    │    4. Executive Report & Dispatch Engine     │
                    ├──────────────────────────────────────────────┤
                    │ • Responsive Executive HTML Email            │
                    │ • High-Resolution Styled PDF Report          │
                    │ • SMTP Dispatch to omersalem@mne.gov.ps &    │
                    │   omersalem2008@gmail.com                    │
                    └──────────────────────────────────────────────┘
```

---

## 4. Component Specifications

### 4.1. Ingestion Layer (`core/connectors/security/`)
- **Fault-Isolation:** Every collector runs inside an isolated error handler. Failure or unreachable status of one device records an operational warning and does not interrupt the remainder of the pipeline.
- **Timeouts & Execution Budget:**
  - Connection timeout: 45 seconds.
  - Log retrieval budget: 120–180 seconds per device (configurable via `MNE_COLLECTOR_TIMEOUT`).
  - Read-Only Guarantee: Strictly read-only queries. Zero configuration changes during collection.
- **Secret Architecture:** All credentials dynamically resolved from `.env` (`MNE_FORTIGATE_PASSWORD`, `MNE_F5_PASSWORD`, `MNE_FMC_PASSWORD`, `MNE_SOPHOS_PASSWORD`, `MNE_AD_PASSWORD`, etc.).

### 4.2. Threat Normalization & Correlation Engine (`core/security_review/engine.py`)
- **Normalized Event Model (`NormalizedSecurityEvent`):**
  - `event_id`: Unique hash based on signature + source + target.
  - `timestamp`: ISO-8601 UTC.
  - `source_device`: Vendor device name.
  - `category`: `INTRUSION`, `MALWARE`, `BRUTE_FORCE`, `WAF_EXPLOIT`, `PHISHING`, `PRIVILEGE_CHANGE`, `SYSTEM_HEALTH`.
  - `threat_name`: Attack signature or descriptive threat.
  - `attacker_ip`: External or rogue internal IP address.
  - `target`: Target server, account username, or URL.
  - `count`: Aggregated event count over the 24h window.
  - `action_taken`: `BLOCKED`, `DROPPED`, `QUARANTINED`, `ALLOWED`.
- **Deduplication:** Collapses high-frequency floods (e.g., 2,500 VPN brute-force hits from a single IP) into one incident record showing count, earliest timestamp, and latest timestamp.
- **Cross-Device Correlation:** Links incidents where the same external IP was observed attacking multiple endpoints (e.g. FortiGate VPN scan + F5 WAF attack).

### 4.3. Standard SOC Risk Classification Rules
- 🔴 **Critical:**
  - High/Critical severity threats where `action_taken == ALLOWED`.
  - Any unsanctioned member added to `Domain Admins` or `Enterprise Admins`.
  - Zero-day sandbox execution alert on Sophos or FortiGate.
  - Core perimeter device HA split-brain or primary security daemon failure.
- 🟠 **High:**
  - Sustained external brute-force attacks (>20 attempts/hour) targeting VPN or OWA.
  - High-confidence malware / ransomware attachments quarantined by Sophos.
  - Confirmed High-severity Snort / IPS / WAF exploit attempts against production VIPs.
  - F5 SSL certificates expiring in less than 7 days.
- 🟡 **Medium:**
  - Standard Active Directory account lockouts (Event 4740).
  - Routine web application reconnaissance probes blocked by F5 ASM.
  - High-volume bulk spam surges blocked by Sophos Email Protection.
  - Non-critical system alerts (CPU/memory warnings, certificates expiring within 30 days).

### 4.4. Remediation Intelligence & Playbooks (`core/security_review/playbooks.py`)
For every **Critical** and **High** incident, the report attaches:
1. **Immediate Containment:** Specific, copy-pasteable CLI commands (FortiGate `diagnose user ban add ...`, F5 `tmsh modify /sys datagroup ...`, PowerShell `Disable-ADAccount ...`).
2. **Permanent Resolution:** Hardening guidance (WAF policy enforcement, firewall address group membership, email domain blacklist).
3. **Assisted Execution Hook (Mode B):**
   - Unique reference tag: `MNE-SEC-<YYYYMMDD>-<INDEX>`.
   - Admin execution trigger: An authorized command that invokes MNE_Brain to prepare and run the fix under owner approval.

### 4.5. Reporting & Dispatch Engine (`core/security_review/reporter.py`)
- **HTML Email Template:**
  - Dark/Light executive layout with official Ministry branding header.
  - Metric summary cards (Critical count, High count, Medium count, Device connectivity status).
  - Multi-vector threat banner (if cross-device attacks exist).
  - Incident details with syntax-highlighted remediation command boxes.
- **PDF Report Generation:**
  - High-resolution, paginated executive PDF generated via Python PDF renderer (`weasyprint` or headless engine).
  - Attached to the email as `MNE_Daily_Security_Report_YYYY-MM-DD.pdf`.
- **SMTP Transport:**
  - Connects to internal Exchange (`172.23.71.36:25` or `:587`) with fallback to configured external SMTP.
  - Recipients: `omersalem@mne.gov.ps`, `omersalem2008@gmail.com`.

### 4.6. Scheduling & CLI Entrypoints (`core/security_review/cli.py`)
- **Scheduled Mode:** Configured as a daily 07:00 AM task via Windows Task Scheduler.
- **Manual / On-Demand Execution:**
  ```powershell
  # Run full review and dispatch email + PDF immediately
  python -m core.security_review.cli --run-now

  # Run review and preview HTML/PDF locally without sending email
  python -m core.security_review.cli --dry-run

  # Execute assisted Mode B remediation for an incident
  python -m core.security_review.cli --remediate MNE-SEC-20260906-01
  ```

---

## 5. Security & Safety Compliance

- **AGENTS.md Adherence:**
  - **Read-Only Default:** All scheduled log collections use read-only commands.
  - **Controlled Autonomous Remediation (Mode B):** Remediations are strictly gated. The agent cannot execute modifications autonomously; it prepares a concrete plan and requires explicit human confirmation.
  - **Zero Credential Exposure:** Passwords and tokens remain strictly in `.env`. Output sanitization scrubs any token or password hashes before rendering into reports.

---

## 6. Verification & Test Plan

1. **Unit Tests (`tests/security_review/`):**
   - Mocked collector responses for FortiGate, F5, FMC, Sophos, AD, and Exchange.
   - Normalization and deduplication logic tests.
   - Severity classifier test cases for Critical, High, and Medium thresholds.
   - Remediation playbook syntax rendering tests.
2. **Integration Tests:**
   - Dry-run verification connecting to mock endpoints or test fixtures.
   - HTML and PDF visual rendering validation.
   - SMTP dispatch validation (with dry-run/mock option).
3. **Live Preflight:**
   - Verification of reachability and read-only credential access to all 6 systems.
