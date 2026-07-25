---
id: "MNE-CONN-FG-BR-NORTH"
title: "conn-fw-fortigate-branch-north"
type: "connection_profile"
status: "active"
device_type: "fortigate_device"
site: "Branch-North"
owner: "SecOps-Team"
last_verified: "2026-07-24"
tags:
  - ministry/connection/branches
---

# Connection Profile: FortiGate Branch North Firewall

Context: [[master-dashboard]] | Related Asset: [[site-branch-north]]

## 🔐 Credentials & Endpoint Properties
- **System Name:** FortiGate North Branch Firewall
- **Device Type:** FortiGate 60E
- **Site:** Branch-North
- **Hostname:** fw-fortigate-branch-north
- **Management IP:** 172.23.90.4
- **FQDN:** fg-branch-north.mne.gov.ps
- **Port:** 22 (SSH)
- **Protocol:** SSH
- **Authentication Method:** Password
- **Username:** admin_readonly
- **Password:** PENDING_USER_INPUT
- **API Token:** N/A
- **Domain:** N/A

## ⚙️ Connection Mechanics & Scope
- **Connection Method:** Netmiko SSH
- **Access Level:** Read-Only
- **Discovery Supported:** Yes
- **Discovery Frequency:** Weekly
- **Status:** Active

## 📝 Operational Notes
- Reachable via HQ IPSec Tunnel.

## 🔗 Related Wiki Pages
- Primary Asset: [[site-branch-north]]
