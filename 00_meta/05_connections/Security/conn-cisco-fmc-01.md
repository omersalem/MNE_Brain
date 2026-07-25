---
id: "MNE-CONN-CISCO-FMC"
title: "conn-cisco-fmc-01"
type: "connection_profile"
status: "active"
device_type: "cisco_fmc"
site: "HQ"
owner: "SecOps-Team"
last_verified: "2026-07-24"
tags:
  - ministry/connection/security
---

# Connection Profile: Cisco FMC Management Center

Context: [[master-dashboard]] | Related Asset: [[cisco-fmc-01]]

## 🔐 Credentials & Endpoint Properties
- **System Name:** Cisco Firewall Management Center (FMC for VMware v7.7.0)
- **Device Type:** FMC Virtual Appliance
- **Site:** HQ
- **Hostname:** cisco-fmc-01
- **Management IP:** `172.23.70.77`
- **FQDN:** fmc.mne.gov.ps
- **Port:** 22 (SSH) / 443 (HTTPS REST API)
- **Protocol:** SSH / HTTPS
- **Authentication Method:** Password
- **Username:** `admin`
- **Password:** `Cisco@2024`
- **API Token:** N/A
- **Domain:** N/A

## ⚙️ Connection Mechanics & Scope
- **Connection Method:** SSH → `expert` bash / FMC REST API
- **Access Level:** Read-Only
- **Discovery Supported:** Yes
- **Discovery Frequency:** Weekly
- **Status:** Active (Validated Live)

## 🔗 Related Wiki Pages
- Primary Asset: [[cisco-fmc-01]]
