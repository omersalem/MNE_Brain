---
id: "MNE-CONN-F5-01"
title: "conn-f5-bigip-01"
type: "connection_profile"
status: "active"
device_type: "f5_object"
site: "HQ"
owner: "SecOps-Team"
last_verified: "2026-07-24"
tags:
  - ministry/connection/security
---

# Connection Profile: F5 BIG-IP r2000 WAF

Context: [[master-dashboard]] | Related Asset: [[f5-vip-public-98]]

## 🔐 Credentials & Endpoint Properties
- **System Name:** F5 BIG-IP r2000 Appliance (v17.5.1.3)
- **Device Type:** BIG-IP r2000
- **Site:** HQ
- **Hostname:** f5-bigip-hq-01
- **Management IP:** `172.23.70.89`
- **FQDN:** f5-hq.mne.gov.ps
- **Port:** 22 (SSH) / 443 (iControl REST)
- **Protocol:** SSH / HTTPS
- **Authentication Method:** Password
- **Username:** `admin`
- **Password:** `Cisco@2024`
- **API Token:** N/A
- **Domain:** N/A

## ⚙️ Connection Mechanics & Scope
- **Connection Method:** SSH `tmsh` read-only commands / iControl REST API
- **Access Level:** Read-Only
- **Discovery Supported:** Yes
- **Discovery Frequency:** Daily
- **Status:** Active (Validated Live)

## 🔗 Related Wiki Pages
- Primary Asset: [[f5-vip-public-98]]
