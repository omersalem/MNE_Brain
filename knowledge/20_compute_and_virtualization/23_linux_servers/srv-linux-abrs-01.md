---
id: MNE-SRV-LINUX-ABRS-01
title: srv-linux-abrs-01
type: abrs_server
status: active
vendor: Canonical
os: Ubuntu 22.04 LTS
site: HQ
owner: AppDev-Team
criticality: critical
environment: production
last_review: '2026-07-24'
tags:
- ministry/compute/abrs
aliases:
- MNE-SRV-LINUX-ABRS-01
source: Canonical Audit
trust_tier: 3
last_verified: '2026-07-27'
related_entities: []
---
# srv-linux-abrs-01

Context: [[index-linux]] | Site: [[site-hq]]

## System Baseline
- **Server IP:** 172.23.79.200 (Greenunit Baseline IP)
- **Application Stack:** Nginx, PHP 8.3 FPM, MariaDB

## Connected Infrastructure
- **Published VIP:** [[f5-vip-public-98]]
- **Edge Firewall:** [[fw-fortigate-hq-01]]
- **ESXi Host:** [[esxi-host-01]]
- **SAN Storage:** [[san-fujitsu-eternus-01]]
