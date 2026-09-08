# FortiAnalyzer 7.4.10 (FAZVM64) — Engineering & Administration Guide

## 📌 Appliance Overview

- **Hostname:** `FAZVM64`
- **Firmware Version:** `v7.4.10-build2778 260126 (GA.M)` (Mature Release)
- **Platform:** `FAZVM64` (FortiAnalyzer-VM 64-bit on VMware vSphere)
- **Serial Number:** `FAZVMSTM24000372`
- **Management IP:** `172.23.71.206/24` (Interface: `port1`)
- **Default Gateway:** `172.23.71.4`
- **DNS Resolvers:** Primary `172.23.71.27` (`MNE-DC1`), Secondary `172.23.71.28` (`MNE-DC2`)
- **Management Protocols:** HTTPS (`443`), SSH (`22`), HTTP redirect (`80`)
- **Telemetry / Ingestion Ports:** TCP/UDP `514` (Syslog/OFTP), TCP `8514` (OFTP over TLS), TCP `5140` (Secure OFTP)

---

## 🏗️ Architecture & Role in MNE Infrastructure

FortiAnalyzer functions as the centralized log repository, Security Operations Center (SOC) analytics engine, compliance archive, and automated reporting hub for the Ministry of National Economy (MNE).

### Ingestion Flow
```
[ Branch Edge Firewalls ] ──(IPsec / MPLS)──┐
  - Bethlehem, Hebron, Jenin, etc.           │
                                             ▼
[ HQ Core Firewalls (FG-MNE) ] ──(TLS 8514)──► [ FortiAnalyzer 172.23.71.206 ]
  - 213.6.17.30 / 172.23.70.4               │
                                             ├─► SQL Database (Analytics / Reports)
                                             └─► Ext4 Archive (Raw Log Storage)
```

---

## 📚 Documentation Index

1. [GUI Configuration Guide](file:///d:/projects/MNE_Brain_v2/docs/company_docs/fortianalyzer-7410/gui-configuration-guide.md)
   * Detailed click-by-click walkthrough for all system, network, security, and administrative tasks in the 7.4.10 web interface.
2. [CLI Configuration Guide](file:///d:/projects/MNE_Brain_v2/docs/company_docs/fortianalyzer-7410/cli-configuration-guide.md)
   * Complete CLI commands, syntax, hierarchy, and examples for configuration, management, and troubleshooting.
3. [Device Registration Guide](file:///d:/projects/MNE_Brain_v2/docs/company_docs/fortianalyzer-7410/device-registration-guide.md)
   * Step-by-step procedures for onboarding FortiGates to FortiAnalyzer using both GUI and CLI on both endpoints.
4. [Storage Quotas & Log Retention](file:///d:/projects/MNE_Brain_v2/docs/company_docs/fortianalyzer-7410/storage-and-log-retention.md)
   * ADOM data policy configuration, analytics vs archive storage split, and expanding quotas to prevent premature log purging.
