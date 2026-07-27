---
id: "MNE-CONN-AD-01"
title: "conn-ad-dc-01"
type: "connection_profile"
status: "active"
device_type: "ad_domain_controller"
site: "HQ"
owner: "SysAdmin-Team"
last_verified: "2026-07-24"
tags:
  - ministry/connection/microsoft
---

# Connection Profile: Active Directory MNE-DC1

Context: [[master-dashboard]] | Related Asset: [[ad-dc-01]]

## 🔐 Credentials & Endpoint Properties
- **System Name:** Active Directory Primary DC (MNE-DC1)
- **Device Type:** Windows Server 2022 AD DS
- **Site:** HQ
- **Hostname:** MNE-DC1
- **Management IP:** `172.23.71.27` (Secondary IP: `172.23.71.173`)
- **FQDN:** MNE-DC1.mne.gov
- **Port:** 5985 (WinRM HTTP)
- **Protocol:** WinRM / WMI
- **Authentication Method:** Domain Account (WinRM NTLM)
- **Username:** `MNEdmin`
- **Password:** `LOADED_FROM_ENV`
- **API Token:** N/A
- **Domain:** `mne.gov` / `mne.gov.ps`

## ⚙️ Connection Mechanics & Scope
- **Connection Method:** PowerShell Remoting over WinRM
- **Access Level:** Read-Only (`Domain Readers`)
- **Discovery Supported:** Yes
- **Discovery Frequency:** Daily
- **Status:** Active (Validated Live)

## 🔗 Related Wiki Pages
- Primary Asset: [[ad-dc-01]]
