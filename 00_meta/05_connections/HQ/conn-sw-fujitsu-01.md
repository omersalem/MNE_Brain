---
id: "MNE-CONN-FUJ-SW1"
title: "conn-sw-fujitsu-01"
type: "connection_profile"
status: "active"
device_type: "fujitsu_core_switch"
site: "HQ"
owner: "Network-Team"
last_verified: "2026-07-24"
tags:
  - ministry/connection/fujitsu
---

# Connection Profile: Fujitsu Core SW1 (MNE-CoreSw1)

Context: [[master-dashboard]] | Related Asset: [[sw-fujitsu-core-02]]

## 🔐 Credentials & Endpoint Properties
- **System Name:** Fujitsu Core Switch 1 (MNE-CoreSw1)
- **Device Type:** Fujitsu PSWITCH 2048P
- **Site:** HQ
- **Hostname:** MNE-CoreSw1
- **Management IP:** `172.23.70.70`
- **FQDN:** coresw1.mne.gov.ps
- **Port:** 22 (SSH)
- **Protocol:** SSH
- **Authentication Method:** Password
- **Username:** `admin`
- **Password:** `LOADED_FROM_ENV`
- **API Token:** N/A
- **Domain:** N/A

## ⚙️ Connection Mechanics & Scope
- **Connection Method:** SSH Read-Only CLI
- **Access Level:** Read-Only
- **Discovery Supported:** Yes
- **Discovery Frequency:** Weekly
- **Status:** Active (Validated Live)

## 🔗 Related Wiki Pages
- Primary Asset: [[sw-fujitsu-core-02]]
