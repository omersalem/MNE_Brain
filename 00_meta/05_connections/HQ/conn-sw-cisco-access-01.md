---
id: "MNE-CONN-CISCO-ACC"
title: "conn-sw-cisco-access-01"
type: "connection_profile"
status: "active"
device_type: "cisco_access_switch"
site: "HQ"
owner: "Network-Team"
last_verified: "2026-07-24"
tags:
  - ministry/connection/cisco
---

# Connection Profile: Cisco Access Switch 01

Context: [[master-dashboard]] | Related Asset: [[sw-cisco-access-01]]

## 🔐 Credentials & Endpoint Properties
- **System Name:** HQ Access Switch Floor 2
- **Device Type:** Catalyst 9300
- **Site:** HQ
- **Hostname:** sw-cisco-access-01
- **Management IP:** 172.23.70.10
- **FQDN:** acc01.mne.gov.ps
- **Port:** 22 (SSH)
- **Protocol:** SSH
- **Authentication Method:** Password
- **Username:** net_readonly
- **Password:** PENDING_USER_INPUT
- **API Token:** N/A
- **Domain:** N/A

## ⚙️ Connection Mechanics & Scope
- **Connection Method:** Netmiko SSH
- **Access Level:** Read-Only
- **Discovery Supported:** Yes
- **Discovery Frequency:** Weekly
- **Status:** Active

## 🔗 Related Wiki Pages
- Primary Asset: [[sw-cisco-access-01]]
