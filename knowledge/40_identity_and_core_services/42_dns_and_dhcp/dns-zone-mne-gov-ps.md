---
id: MNE-DNS-ZONE-GOV
title: dns-zone-mne-gov-ps
type: dns_zone
status: active
vendor: Microsoft
site: HQ
owner: SysAdmin-Team
criticality: critical
environment: production
last_review: '2026-07-24'
tags:
- ministry/microsoft/dns
aliases:
- MNE-DNS-ZONE-GOV
source: Canonical Audit
trust_tier: 3
last_verified: '2026-07-27'
related_entities: []
---
# dns-zone-mne-gov-ps

Context: [[index-microsoft]] | Primary DC: [[ad-dc-01]]

## Zone Records
- `mne.gov.ps` Authoritative Primary Zone
- Autodiscover Record -> [[f5-vip-public-98]]
- Exchange Mail Record -> [[exch-srv-01]]
