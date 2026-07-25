---
id: "MNE-TMPL-CONN"
title: "Connection Profile Template"
type: "connection_profile"
status: "active"
device_type: "fortigate|cisco_switch|cisco_router|f5_waf|windows_ad|exchange|vcenter|esxi|fujitsu_san|linux"
site: "HQ|Branch"
owner: "SysAdmin-Team|Network-Team|SecOps-Team"
last_verified: "YYYY-MM-DD"
tags:
  - ministry/connection
---

# Connection Profile: {{title}}

Context: [[master-dashboard]] | Category: Connection Profiles

## 🔐 Credentials & Endpoint Properties
- **System Name:** {{system_name}}
- **Device Type:** {{device_type}}
- **Site:** {{site}}
- **Hostname:** {{hostname}}
- **Management IP:** {{mgmt_ip}}
- **FQDN:** {{fqdn}}
- **Port:** {{port}}
- **Protocol:** SSH / HTTPS / WinRM / SNMP
- **Authentication Method:** Password / SSH Key / API Token
- **Username:** {{username}}
- **Password:** {{password}}
- **API Token:** {{api_token}}
- **Domain:** {{domain}}

## ⚙️ Connection Mechanics & Scope
- **Connection Method:** Netmiko SSH / iControl REST / WinRM PowerShell / vSphere REST
- **Access Level:** Read-Only
- **Discovery Supported:** Yes
- **Discovery Frequency:** Daily / Weekly
- **Status:** Active / Pending Verification

## 📝 Operational Notes
- Connection instructions, jump host details, or specific port requirements.

## 🔗 Related Wiki Pages
- Primary Asset: [[{{related_asset}}]]
- Relevant Index: [[index-infrastructure]]
