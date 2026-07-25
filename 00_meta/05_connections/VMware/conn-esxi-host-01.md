---
id: "MNE-CONN-ESXI-01"
title: "conn-esxi-host-01"
type: "connection_profile"
status: "active"
device_type: "esxi_host"
site: "HQ"
owner: "SysAdmin-Team"
last_verified: "2026-07-24"
tags:
  - ministry/connection/vmware
---

# Connection Profile: ESXi Host 01

Context: [[master-dashboard]] | Related Asset: [[esxi-host-01]]

## 🔐 Credentials & Endpoint Properties
- **System Name:** ESXi Hypervisor Host 01
- **Device Type:** Fujitsu PRIMERGY / VMware ESXi 7.0
- **Site:** HQ
- **Hostname:** esxi-host-01
- **Management IP:** 172.23.69.41
- **FQDN:** esxi01.mne.gov.ps
- **Port:** 443 (HTTPS) / 22 (SSH)
- **Protocol:** HTTPS / SSH
- **Authentication Method:** Managed via vCenter / Local Root Read-Only
- **Username:** root_readonly
- **Password:** PENDING_USER_INPUT
- **API Token:** N/A
- **Domain:** mne.gov.ps

## ⚙️ Connection Mechanics & Scope
- **Connection Method:** Managed via [[conn-vcenter-main]] / ESXCLI Read-Only
- **Access Level:** Read-Only
- **Discovery Supported:** Yes
- **Discovery Frequency:** Daily
- **Status:** Active

## 🔗 Related Wiki Pages
- Primary Asset: [[esxi-host-01]]
