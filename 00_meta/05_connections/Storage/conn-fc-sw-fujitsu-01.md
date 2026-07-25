---
id: "MNE-CONN-FUJ-FC-01"
title: "conn-fc-sw-fujitsu-01"
type: "connection_profile"
status: "active"
device_type: "fc_switch"
site: "HQ"
owner: "SysAdmin-Team"
last_verified: "2026-07-24"
tags:
  - ministry/connection/storage
---

# Connection Profile: Fujitsu FC Switch 01

Context: [[master-dashboard]] | Related Asset: [[fc-sw-fujitsu-01]]

## 🔐 Credentials & Endpoint Properties
- **System Name:** Fujitsu Fibre Channel Switch 01
- **Device Type:** Brocade / Fujitsu FC Switch
- **Site:** HQ
- **Hostname:** fc-sw-fujitsu-01
- **Management IP:** 172.23.68.10
- **FQDN:** fcsw01.mne.gov.ps
- **Port:** 22 (SSH)
- **Protocol:** SSH
- **Authentication Method:** Password
- **Username:** user
- **Password:** PENDING_USER_INPUT
- **API Token:** N/A
- **Domain:** N/A

## ⚙️ Connection Mechanics & Scope
- **Connection Method:** Brocade SSH CLI (`switchshow`, `zoneshow`)
- **Access Level:** Read-Only (User Role)
- **Discovery Supported:** Yes
- **Discovery Frequency:** Weekly
- **Status:** Active

## 🔗 Related Wiki Pages
- Primary Asset: [[fc-sw-fujitsu-01]]
