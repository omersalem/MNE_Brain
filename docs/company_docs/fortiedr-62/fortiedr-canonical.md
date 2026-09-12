---
id: "edr-fortiedr-cloud-01"
name: "MNE FortiEDR Cloud Central Manager & Endpoint Protection"
category: "network"
aliases: ["fortiedr", "fortiedr-cloud", "fortiedrconnectil", "edr-fortiedr-cloud-01", "mne-edr", "ensilo", "fortiedrconnectil.console.ensilo.com"]
hostname: "fortiedrconnectil.console.ensilo.com"
fqdn: "fortiedrconnectil.console.ensilo.com"
ip: "fortiedrconnectil.console.ensilo.com"
vlan: "cloud"
services: ["edr-management", "endpoint-prevention", "threat-hunting", "communication-control", "collector-registration"]
owner: "Cybersecurity & Endpoint Infrastructure Team"
related_entities: ["fw-fortigate-hq-01", "dc-windows-ad-01", "faz-fortianalyzer-hq-01"]
knowledge_status: "documented"
source: "https://docs.fortinet.com/document/fortiedr/6.2.0/administration-guide/354083/introducing-fortiedr"
last_verified: null
freshness_ttl_hours: 720
---

# Canonical Facts — MNE FortiEDR Cloud Central Manager & Endpoint Protection

> **Entity ID:** `edr-fortiedr-cloud-01`  
> **Platform:** `fortinet_fortiedr`  
> **Software Release:** `6.2`  
> **Trust Level:** Level 3 (Canonical Vault Fact)  
> **Tenant Domain:** `fortiedrconnectil.console.ensilo.com`  
> **Multi-Tenancy Organization:** `MNE`  
> **Primary Administrator:** `omersalem`  
> **Last Verified:** 2026-09-12T10:07:00Z  

---

## 🏛️ System Identity & Architecture

FortiEDR is a distributed endpoint detection, prevention, and response platform deployed in Fortinet Cloud for Ministry of National Economy (MNE). The installation is multi-tenant and configured for organization **MNE**.

### Architectural Roles:
1. **FortiEDR Central Manager (Cloud Console):**
   - Web GUI and REST API endpoint: `https://fortiedrconnectil.console.ensilo.com`
   - Management port: `443/tcp` (HTTPS / TLS 1.3)
   - Handles policy administration, incident triage, forensics, collector groups, and exception management.
2. **FortiEDR Cloud Core:**
   - Real-time kernel-level event evaluation and malware prevention engine.
   - Endpoint real-time communication port: `555/tcp`.
3. **FortiEDR Cloud Aggregators:**
   - Distributed collector registration, configuration delivery, and telemetry dispatchers.
   - Collector-to-Aggregator communication port: `8081/tcp`.
4. **Threat Hunting Repository:**
   - Scalable repository indexing all raw historical telemetry for Lucene-based forensics.
5. **FortiEDR Collectors:**
   - Lightweight kernel and user-space drivers deployed on Windows, Linux, and macOS endpoints.

---

## 🔌 Network Communication & Port Matrix

| Source | Destination | Destination Port | Protocol | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| Endpoint Collector | FortiEDR Aggregator | `8081/tcp` | TLS / Encrypted TCP | Registration, keepalives, and telemetry |
| Endpoint Collector | FortiEDR Core | `555/tcp` | TLS / Custom Encrypted | Real-time execution prevention |
| Admin / MNE Brain | FortiEDR Central Manager | `443/tcp` | HTTPS | Management GUI and REST API |
| FortiEDR Cloud | Endpoint (Direct) | None | Inverted | Collectors initiate all outbound tunnels |

---

## ⚙️ Core Configuration Baseline for MNE Organization

- **Organization Name:** `MNE`
- **Global Operating Mode:** `Prevention` (Toggle in top header bar)
- **Authentication:** Local admin `omersalem`, integration ready for LDAP / Active Directory (`MNE-DC1.mne.gov`) and SAML SSO.
- **Collector Deployment Parameter:**
  ```powershell
  msiexec /i FortiEDRCollectorInstaller64.msi /qn AGG=fortiedrconnectil.console.ensilo.com:8081 PWD=%PWD% ORG="MNE" DEFGROUP="Default Collector Group"
  ```
- **Related Security Infrastructure:**
  - `fw-fortigate-hq-01`: Enterprise perimeter firewall controlling outbound endpoint connectivity.
  - `dc-windows-ad-01`: Domain Controller providing identity mapping and GPO distribution.
  - `faz-fortianalyzer-hq-01`: Central syslog aggregator receiving high-severity EDR alerts.
