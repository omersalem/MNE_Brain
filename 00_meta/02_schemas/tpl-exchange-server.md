---
id: "MNE-TMPL-EXCHANGE"
title: "Exchange Server Template"
type: "exchange_server"
status: "active"
vendor: "Microsoft"
os: "Windows Server 2022"
version: "Exchange Server 2019 CU13"
site: "HQ"
owner: "SysAdmin-Team"
criticality: "critical"
environment: "production"
last_review: "YYYY-MM-DD"
tags:
  - ministry/microsoft/exchange
---

# {{title}}

Context: [[index-microsoft]] | Site: [[site-hq]]

## Exchange Server Details
- **Server FQDN:** mail.mne.gov.ps
- **Management IP:** 
- **Roles:** Mailbox / Client Access Service (CAS)
- **DAG Group:** [[exch-dag-main]]

## Infrastructure & Service Wiring
- **Active Directory:** [[ad-dc-01]]
- **DNS Resolution:** [[dns-zone-mne-gov-ps]]
- **WAF Publishing:** [[f5-vip-public-98]]
- **Storage Target:** [[san-fujitsu-eternus-01]]
- **VMware Host:** [[esxi-host-01]]
