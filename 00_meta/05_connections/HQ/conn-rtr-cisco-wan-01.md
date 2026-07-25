---
id: "MNE-CONN-CISCO-RTR"
title: "conn-rtr-cisco-wan-01"
type: "connection_profile"
status: "active"
device_type: "cisco_router"
site: "HQ"
owner: "Network-Team"
last_verified: "2026-07-24"
tags:
  - ministry/connection/cisco
---

# Connection Profile: Cisco WAN Router 01

Context: [[master-dashboard]] | Related Asset: [[rtr-cisco-wan-01]]

## 🔐 Credentials & Endpoint Properties
- **System Name:** HQ Cisco WAN Router
- **Device Type:** ISR 4431
- **Site:** HQ
- **Hostname:** rtr-cisco-wan-01
- **Management IP:** 172.23.70.254
- **FQDN:** wan01.mne.gov.ps
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
- Primary Asset: [[rtr-cisco-wan-01]]
