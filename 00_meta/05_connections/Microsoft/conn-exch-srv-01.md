---
id: "MNE-CONN-EXCH-01"
title: "conn-exch-srv-01"
type: "connection_profile"
status: "active"
device_type: "exchange_server"
site: "HQ"
owner: "SysAdmin-Team"
last_verified: "2026-07-24"
tags:
  - ministry/connection/microsoft
---

# Connection Profile: EXCHANGESRV2 (Exchange 2019)

Context: [[master-dashboard]] | Related Asset: [[exch-srv-01]]

## 🔐 Credentials & Endpoint Properties
- **System Name:** Secondary Exchange Mailbox Server (EXCHANGESRV2)
- **Device Type:** Exchange Server 2019
- **Site:** HQ
- **Hostname:** EXCHANGESRV2
- **Management IP:** `172.23.71.36`
- **FQDN:** EXCHANGESRV2.mne.gov
- **Port:** 5985 (WinRM)
- **Protocol:** WinRM + Exchange Management Shell PowerShell
- **Authentication Method:** Domain Account
- **Username:** `MNEdmin`
- **Password:** `omersalem570-6127`
- **API Token:** N/A
- **Domain:** `mne.gov`

## ⚙️ Connection Mechanics & Scope
- **Connection Method:** Remote Exchange Management Shell (EMS)
- **Access Level:** Read-Only (`View-Only Organization Management`)
- **Discovery Supported:** Yes
- **Discovery Frequency:** Daily
- **Status:** Active (Validated Live)

## 🔗 Related Wiki Pages
- Primary Asset: [[exch-srv-01]]
