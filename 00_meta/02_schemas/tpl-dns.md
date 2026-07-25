---
id: "MNE-TMPL-DNS"
title: "DNS Zone Template"
type: "dns_zone"
status: "active"
vendor: "Microsoft"
site: "HQ"
owner: "SysAdmin-Team"
criticality: "critical"
environment: "production"
last_review: "YYYY-MM-DD"
tags:
  - ministry/microsoft/dns
---

# {{title}}

Context: [[index-microsoft]] | Site: [[site-hq]]

## Zone Metadata
- **Zone Name:** mne.gov.ps
- **Primary DNS Server:** [[ad-dc-01]]
- **Dynamic Updates:** Secure Only (AD-Integrated)

## Key Records
- `autodiscover.mne.gov.ps` -> [[f5-vip-public-98]]
- `mail.mne.gov.ps` -> [[exch-srv-01]]
