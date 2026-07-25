---
id: "MNE-CONN-SCCM-01"
title: "conn-sccm-srv-01"
type: "connection_profile"
status: "active"
device_type: "sccm_server"
site: "HQ"
owner: "SysAdmin-Team"
last_verified: "2026-07-24"
tags:
  - ministry/connection/microsoft
---

# Connection Profile: SCCM (MECM) Server

Context: [[master-dashboard]] | Related Asset: [[sccm-srv-01]]

## 🔐 Credentials & Endpoint Properties
- **System Name:** Primary SCCM Infrastructure Server
- **Device Type:** MECM 2309 / Windows Server 2022
- **Site:** HQ
- **Hostname:** sccm-srv-01
- **Management IP:** 172.23.71.80
- **FQDN:** sccm.mne.gov.ps
- **Port:** 5985 (WinRM) / WMI
- **Protocol:** WinRM / WMI
- **Authentication Method:** Domain Account
- **Username:** svc_discovery_read
- **Password:** PENDING_USER_INPUT
- **API Token:** N/A
- **Domain:** mne.gov.ps

## ⚙️ Connection Mechanics & Scope
- **Connection Method:** WMI Query / SCCM PowerShell Module (Read-Only)
- **Access Level:** Read-Only Analyst
- **Discovery Supported:** Yes
- **Discovery Frequency:** Weekly
- **Status:** Active

## 🔗 Related Wiki Pages
- Primary Asset: [[sccm-srv-01]]
