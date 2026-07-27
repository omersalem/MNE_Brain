---
id: MNE-SAN-FUJ-ETERNUS-01
title: san-fujitsu-eternus-01
type: fujitsu_san
status: active
vendor: Fujitsu
model: ETERNUS DX200
site: HQ
owner: SysAdmin-Team
criticality: critical
environment: production
last_review: '2026-07-24'
tags:
- ministry/storage/fujitsu-san
aliases:
- MNE-SAN-FUJ-ETERNUS-01
source: Canonical Audit
trust_tier: 3
last_verified: '2026-07-27'
related_entities: []
---
# san-fujitsu-eternus-01

Context: [[index-storage]] | Site: [[site-hq]]

## Storage Specifications
- **Management IP:** 172.23.68.20
- **FC Switch Connection:** [[fc-sw-fujitsu-01]]
- **VMware Datastores Provided:** Used by [[esxi-host-01]] for [[exch-srv-01]] and [[srv-linux-abrs-01]].
