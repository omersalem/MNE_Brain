---
id: "MNE-CONN-ABRS-01"
title: "conn-srv-linux-abrs-01"
type: "connection_profile"
status: "active"
device_type: "abrs_server"
site: "HQ"
owner: "AppDev-Team"
last_verified: "2026-07-24"
tags:
  - ministry/connection/linux
---

# Connection Profile: ABRS Linux Server

Context: [[master-dashboard]] | Related Asset: [[srv-linux-abrs-01]]

## 🔐 Credentials & Endpoint Properties
- **System Name:** ABRS Production Web Server
- **Device Type:** Ubuntu 22.04 LTS
- **Site:** HQ
- **Hostname:** srv-linux-abrs-01
- **Management IP:** 172.23.79.200
- **FQDN:** greenunit.mne.gov.ps
- **Port:** 22 (SSH)
- **Protocol:** SSH
- **Authentication Method:** SSH Key (Ed25519) / Password
- **Username:** sysadmin_read
- **Password:** PENDING_USER_INPUT
- **API Token:** N/A
- **Domain:** N/A

## ⚙️ Connection Mechanics & Scope
- **Connection Method:** Paramiko / OpenSSH CLI
- **Access Level:** Read-Only
- **Discovery Supported:** Yes
- **Discovery Frequency:** Daily
- **Status:** Active

## 📝 Operational Notes
- Tested reachability on 172.23.79.200:22.
- Executes `hostnamectl`, `ss -tuln`, `ufw status numbered`, `systemctl is-active`.

## 🔗 Related Wiki Pages
- Primary Asset: [[srv-linux-abrs-01]]
