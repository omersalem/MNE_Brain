---
id: "MNE-CONN-FUJ-SAN-01"
title: "conn-san-fujitsu-eternus-01"
type: "connection_profile"
status: "active"
device_type: "fujitsu_san"
site: "HQ"
owner: "SysAdmin-Team"
last_verified: "2026-07-24"
tags:
  - ministry/connection/storage
---

# Connection Profile: Fujitsu SAN Storage Array

Context: [[master-dashboard]] | Related Asset: [[san-fujitsu-eternus-01]]

## 🔐 Credentials & Endpoint Properties
- **System Name:** Fujitsu ETERNUS SAN Storage
- **Device Type:** ETERNUS DX200
- **Site:** HQ
- **Hostname:** san-fujitsu-eternus-01
- **Management IP:** 172.23.68.20
- **FQDN:** san01.mne.gov.ps
- **Port:** 443 (HTTPS) / 22 (SSH CLI)
- **Protocol:** HTTPS / SSH
- **Authentication Method:** Password
- **Username:** monitor_user
- **Password:** PENDING_USER_INPUT
- **API Token:** N/A
- **Domain:** N/A

## ⚙️ Connection Mechanics & Scope
- **Connection Method:** Fujitsu ETERNUS CLI read calls / ETERNUS Web GUI API
- **Access Level:** Read-Only (Monitor Role)
- **Discovery Supported:** Yes
- **Discovery Frequency:** Weekly
- **Status:** Active

## 🔗 Related Wiki Pages
- Primary Asset: [[san-fujitsu-eternus-01]]
