---
id: "MNE-CONN-VCENTER"
title: "conn-vcenter-main"
type: "connection_profile"
status: "active"
device_type: "vcenter_server"
site: "HQ"
owner: "SysAdmin-Team"
last_verified: "2026-07-24"
tags:
  - ministry/connection/vmware
---

# Connection Profile: vCenter Server Appliance (VCSA 7.0.3)

Context: [[master-dashboard]] | Related Asset: [[vcenter-main]]

## 🔐 Credentials & Endpoint Properties
- **System Name:** vCenter Server Appliance
- **Device Type:** VCSA 7.0.3
- **Site:** HQ
- **Hostname:** vcenter-main
- **Management IP:** `172.23.69.38`
- **FQDN:** vcenter.mne.gov.ps
- **Port:** 443 (vSphere REST API / PowerCLI) / 22 (SSH `shell` bash)
- **Protocol:** HTTPS / SSH
- **Authentication Method:** Password
- **Username:** `root`
- **Password:** `Kh@fud$2021`
- **API Token:** N/A
- **Domain:** `vsphere.local`

## ⚙️ Connection Mechanics & Scope
- **Connection Method:** vSphere Automation REST API / PowerCLI / SSH
- **Access Level:** Read-Only
- **Discovery Supported:** Yes
- **Discovery Frequency:** Daily
- **Status:** Active (Validated Live)

## 🔗 Related Wiki Pages
- Primary Asset: [[vcenter-main]]
