---
id: "faz-fortianalyzer-hq-01"
name: "HQ Central Log Analyzer (FortiAnalyzer VM64)"
category: "network"
aliases: ["fortianalyzer", "faz", "fazvm64", "faz-fortianalyzer-hq-01", "172.23.71.206", "forti-analyzer"]
hostname: "FAZVM64"
fqdn: "FAZVM64.mne.gov.ps"
ip: "172.23.71.206"
vlan: "71"
services: ["log-collector", "analytics", "event-management", "reporting", "soc-monitoring"]
owner: "SecOps-Team"
related_entities: ["fw-fortigate-hq-01", "sw-cisco-core-01", "vc-vmware-hq-01"]
knowledge_status: "unverified"
source: "live_system_verification"
last_verified: null
freshness_ttl_hours: 720
---

# Canonical Facts — FortiAnalyzer Central Logging & Analytics (FAZVM64)

> **Entity ID:** `faz-fortianalyzer-hq-01`  
> **Trust Level:** Level 5 (Live Verified Sovereign Fact)  
> **Last Verified:** 2026-09-07T11:13:00Z  

---

## 🏛️ Device Identity & System Overview
- **Device Name / Hostname:** `FAZVM64`
- **Platform Type:** `FAZVM64` (FortiAnalyzer-VM64)
- **Serial Number:** `FAZVMSTM24000372`
- **Firmware Version:** `v7.4.10-build2778 260126 (GA.M)` (Mature Release)
- **License Status:** Valid GA Certified VM License
- **High Availability (HA):** Standalone
- **Administrative Domains (ADOM):** Root ADOM active (ADOM Mode: Normal)
- **Time Zone:** `(GMT+2:00) Jerusalem`

---

## 🔌 Network & Interface Configuration
- **Management Interface:** `port1`
- **Management IP:** `172.23.71.206 / 255.255.255.0` (VLAN 71 Server/Management)
- **Default Gateway:** `172.23.71.4` (via `port1`)
- **Primary DNS:** `172.23.71.27` (`MNE-DC1.mne.gov.ps`)
- **Secondary DNS:** `172.23.71.28` (`MNE-DC2.mne.gov.ps`)
- **Allowed Administrative Access on port1:** `ping`, `https` (Port 443), `ssh` (Port 22), `http` (Port 80)
- **SSH Host Key Fingerprint:** `ssh-ed25519 256 SHA256:KujJJ7526WSymP5Z5Yj9MrZY4du0y2+y9uQXfIkAHqw`

---

## 💾 Storage & Quota Allocation (Live Audit)
- **Total System Disk:** `491.1 GB` (Virtual Disk, Ext4 file system)
- **Used Disk:** `89.0 GB` (18.1% overall utilization)
- **Available Disk Space:** `402.1 GB`
- **Reserved System Space:** `50.0 GB` (10.2%)
- **Total Quota Available:** `441.1 GB`
- **Allocated Quota to ADOM root:** `63.0 GB` (14.3% allocated)
- **ADOM `root` Storage Breakdown:**
  - **Archive Raw Logs:** Retention: `100 days` | Quota: `18.9 GB` | Used: `16.9 GB` (89.5% used)
  - **SQL Database Analytics:** Retention: `60 days` | Quota: `44.1 GB` | Used: `40.3 GB` (91.4% used)

---

## 🛡️ Managed Devices Inventory (14 FortiGate Firewalls)
FortiAnalyzer is actively collecting and indexing security telemetry from 14 ministry firewalls:
1. **`FG-MNE` (HQ Core Firewall):** IP `213.6.17.30`, Serial `FG4H1FT924905842` (FortiOS 7.x, 14.3 GB log volume)
2. **`FW-MNE-Bethlahem`:** IP `172.27.13.14`, Serial `FGT71GTK25008298`
3. **`FW-MNE-Hebron`:** IP `172.27.13.62`, Serial `FGT71GTK25009263`
4. **`FW-MNE-GoldH` (Hebron Gold):** IP `172.27.13.42`, Serial `FGT71GTK25009380`
5. **`FG-Jenin`:** IP `172.27.13.26`, Serial `FGT71GTK25009456`
6. **`FG-Jericho` / `FW-MNE-Jericho`:** IP `172.27.13.38`, Serial `FGT60FTK2109C588` / `FGT71GTK25013043`
7. **`FG-Quds` (Jerusalem):** IP `172.27.13.22`, Serial `FGT60FTK2109C4QH`
8. **`FW-MNE-Nablus`:** IP `172.27.13.58`, Serial `FGT71GTK25008875`
9. **`FW-MNE-Qalqilyah`:** IP `172.27.13.46`, Serial `FGT71GTK25009552`
10. **`FW-MNE-Salfeet`:** IP `172.27.13.30`, Serial `FGT71GTK25009726`
11. **`FW-MNE-Tubas`:** IP `172.27.13.18`, Serial `FGT71GTK25009251`
12. **`GoldN` (Nablus Gold):** IP `172.27.13.34`, Serial `FGT71GTK25009573`
13. **`MNE-Tulkarem`:** IP `172.27.13.50`, Serial `FGT71GTK25009434`
14. **`FG-GoldR` / `FW-MNE-GoldR` (Ramallah Gold):** IP `172.27.13.54`, Serial `FGT81FTK21001015` / `FGT71GTK25013189`
