---
id: "MNE-CONN-FG-HQ"
title: "conn-fw-fortigate-hq"
type: "connection_profile"
status: "active"
device_type: "fortigate_device"
site: "HQ"
owner: "SecOps-Team"
last_verified: "2026-07-24"
tags:
  - ministry/connection/security
---

# Connection Profile: FortiGate FG-MNE (401F)

Context: [[master-dashboard]] | Related Asset: [[fw-fortigate-hq-01]]

## 🔐 Credentials & Endpoint Properties
- **System Name:** FortiGate HQ Perimeter Firewall (FG-MNE)
- **Device Type:** FortiGate 401F (FortiOS 7.4.11)
- **Site:** HQ
- **Hostname:** FG-MNE
- **Management IP:** `172.23.70.4`
- **FQDN:** fg-mne.mne.gov.ps
- **Port:** 22 (SSH) / 443 (HTTPS REST API)
- **Protocol:** SSH / HTTPS
- **Authentication Method:** Password / SSH Key
- **Username:** `adminread`
- **Password:** `omersalem570-6127`
- **API Token:** N/A
- **Domain:** N/A

## ⚙️ Connection Mechanics & Scope
- **Connection Method:** Netmiko SSH / FortiOS REST API
- **Access Level:** Read-Only
- **Discovery Supported:** Yes
- **Discovery Frequency:** Daily
- **Status:** Active (Validated Live)

## 📝 Operational Notes
- Verified live SSH reachability on `172.23.70.4:22`.
- Executes `get system status`, `show firewall policy`, `show vpn ssl settings`.

## 🔗 Related Wiki Pages
- Primary Asset: [[fw-fortigate-hq-01]]
