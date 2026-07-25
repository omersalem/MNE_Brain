---
id: "MNE-CONN-CISCO-CORE"
title: "conn-sw-cisco-core-01"
type: "connection_profile"
status: "active"
device_type: "cisco_core_switch"
site: "HQ"
owner: "Network-Team"
last_verified: "2026-07-24"
tags:
  - ministry/connection/cisco
---

# Connection Profile: Cisco Core Switch (CoreSwitch1)

Context: [[master-dashboard]] | Related Asset: [[sw-cisco-core-01]]

## 🔐 Credentials & Endpoint Properties
- **System Name:** Cisco Core Switch 1 Stack
- **Device Type:** Catalyst 9500 Stack
- **Site:** HQ
- **Hostname:** CoreSwitch1
- **Management IP:** `172.23.70.254`
- **FQDN:** ciscocore.mne.gov.ps
- **Port:** 22 (SSH)
- **Protocol:** SSH
- **Authentication Method:** Password (User EXEC)
- **Username:** `admin`
- **Password:** `Axizo@1234`
- **API Token:** N/A
- **Domain:** N/A

## ⚙️ Connection Mechanics & Scope
- **Connection Method:** Netmiko SSH (User Exec Priv 1)
- **Access Level:** Read-Only
- **Discovery Supported:** Yes
- **Discovery Frequency:** Weekly
- **Status:** Active (Validated Live)

## 🔗 Related Wiki Pages
- Primary Asset: [[sw-cisco-core-01]]
