---
id: "MNE-CONN-DNS-01"
title: "conn-dns-srv-01"
type: "connection_profile"
status: "active"
device_type: "dns_zone"
site: "HQ"
owner: "SysAdmin-Team"
last_verified: "2026-07-24"
tags:
  - ministry/connection/microsoft
---

# Connection Profile: Microsoft DNS Server

Context: [[master-dashboard]] | Related Asset: [[dns-zone-mne-gov-ps]]

## 🔐 Credentials & Endpoint Properties
- **System Name:** Authoritative Primary DNS Server
- **Device Type:** Windows DNS Server (AD-Integrated)
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
- **Connection Method:** PowerShell `Get-DnsServerZone` & `Get-DnsServerResourceRecord`
- **Access Level:** Read-Only
- **Discovery Supported:** Yes
- **Discovery Frequency:** Daily
- **Status:** Active

## 🔗 Related Wiki Pages
- Primary Asset: [[dns-zone-mne-gov-ps]]
