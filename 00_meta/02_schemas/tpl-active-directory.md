---
id: "MNE-TMPL-AD"
title: "Active Directory Domain Controller Template"
type: "ad_domain_controller"
status: "active"
vendor: "Microsoft"
os: "Windows Server 2022"
site: "HQ"
owner: "SysAdmin-Team"
criticality: "critical"
environment: "production"
last_review: "YYYY-MM-DD"
tags:
  - ministry/microsoft/active-directory
---

# {{title}}

Context: [[index-microsoft]] | Site: [[site-hq]]

## Domain Services Baseline
- **Domain Name:** mne.gov.ps
- **DC IP Address:** 
- **FSMO Roles:** Schema / Naming / PDC / RID / Infrastructure

## Dependent Systems
- [[exch-srv-01]]
- [[sccm-srv-01]]
- [[dns-zone-mne-gov-ps]]
