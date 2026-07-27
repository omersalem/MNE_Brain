---
id: "MNE-CONN-VEEAM-01"
title: "conn-veeam-backup-01"
type: "connection_profile"
status: "active"
device_type: "veeam_backup_server"
site: "HQ"
owner: "SysAdmin-Team"
last_verified: "2026-07-24"
tags:
  - ministry/connection/storage
---

# Connection Profile: Veeam Backup Server (FUJI-BACKUP-SER)

Context: [[master-dashboard]] | Related Asset: [[index-storage]]

## 🔐 Credentials & Endpoint Properties
- **System Name:** Veeam Backup & Replication Server (FUJI-BACKUP-SER)
- **Device Type:** Windows Server 2019 (Workgroup Standalone)
- **Site:** HQ
- **Hostname:** FUJI-BACKUP-SER
- **Management IP:** `172.23.69.60`
- **FQDN:** fuji-backup-ser.mne.gov.ps
- **Port:** 5985 (WinRM)
- **Protocol:** WinRM / NTLM
- **Authentication Method:** Local Administrator
- **Username:** `administrator`
- **Password:** `LOADED_FROM_ENV`
- **API Token:** N/A
- **Domain:** WORKGROUP

## ⚙️ Connection Mechanics & Scope
- **Connection Method:** PowerShell Remoting over WinRM / Veeam PowerShell Module
- **Access Level:** Read-Only
- **Discovery Supported:** Yes
- **Discovery Frequency:** Weekly
- **Status:** Active (Validated Live)

## 🔗 Related Wiki Pages
- Primary Index: [[index-storage]]
