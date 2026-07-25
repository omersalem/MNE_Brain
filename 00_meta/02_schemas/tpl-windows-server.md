---
id: "MNE-TMPL-WIN-SRV"
title: "Windows Server Template"
type: "windows_server"
status: "active"
vendor: "Microsoft"
os: "Windows Server 2022"
site: "HQ"
owner: "SysAdmin-Team"
criticality: "medium"
environment: "production"
last_review: "YYYY-MM-DD"
tags:
  - ministry/compute/windows
---

# {{title}}

Context: [[index-microsoft]] | Host: [[esxi-host-01]]

## Server Baseline
- **Management IP:** 
- **Active Directory Domain:** [[ad-domain-mne]]

## Roles & Services
- IIS / Web Server
- Backup / Storage Agent
