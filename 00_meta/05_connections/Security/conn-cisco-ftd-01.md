---
id: "MNE-CONN-CISCO-FTD"
title: "conn-cisco-ftd-01"
type: "connection_profile"
status: "active"
device_type: "cisco_ftd"
site: "HQ"
owner: "SecOps-Team"
last_verified: "2026-07-24"
tags:
  - ministry/connection/security
---

# Connection Profile: Cisco FTD Firewall Sensor (FTD-01)

Context: [[master-dashboard]] | Related Asset: [[cisco-ftd-01]]

## 🔐 Credentials & Endpoint Properties
- **System Name:** Cisco Secure Firewall 3105 Threat Defense (FTD-01)
- **Device Type:** Firepower 3105 (v7.6.2)
- **Site:** HQ
- **Hostname:** FTD-01.mne.gov.ps
- **Management IP:** `172.23.70.78`
- **FQDN:** ftd-01.mne.gov.ps
- **Port:** 22 (SSH) / 443 (HTTPS)
- **Protocol:** SSH / HTTPS
- **Authentication Method:** Password
- **Username:** `admin`
- **Password:** `LOADED_FROM_ENV`
- **API Token:** N/A
- **Domain:** N/A

## ⚙️ Connection Mechanics & Scope
- **Connection Method:** SSH CLI / Managed via FMC [[conn-cisco-fmc-01]]
- **Access Level:** Read-Only
- **Discovery Supported:** Yes
- **Discovery Frequency:** Weekly
- **Status:** Active (Validated Live)

## 🔗 Related Wiki Pages
- Primary Asset: [[cisco-ftd-01]]
