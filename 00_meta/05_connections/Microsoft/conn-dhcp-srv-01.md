---
id: "MNE-CONN-DHCP-01"
title: "conn-dhcp-srv-01"
type: "connection_profile"
status: "active"
device_type: "dhcp_scope"
site: "HQ"
owner: "SysAdmin-Team"
last_verified: "2026-07-24"
tags:
  - ministry/connection/microsoft
---

# Connection Profile: Microsoft DHCP Server

Context: [[master-dashboard]] | Related Asset: [[dhcp-scope-user-lan]]

## 🔐 Credentials & Endpoint Properties
- **System Name:** Primary DHCP Server
- **Device Type:** Windows Server 2022 DHCP
- **Site:** HQ
- **Hostname:** ad-dc-01
- **Management IP:** 172.23.71.27
- **FQDN:** dc01.mne.gov.ps
- **Port:** 5985 (WinRM)
- **Protocol:** WinRM
- **Authentication Method:** Domain Account
- **Username:** svc_discovery_read
- **Password:** PENDING_USER_INPUT
- **API Token:** N/A
- **Domain:** mne.gov.ps

## ⚙️ Connection Mechanics & Scope
- **Connection Method:** PowerShell `Get-DhcpServerv4Scope`
- **Access Level:** Read-Only
- **Discovery Supported:** Yes
- **Discovery Frequency:** Weekly
- **Status:** Active

## 🔗 Related Wiki Pages
- Primary Asset: [[dhcp-scope-user-lan]]
