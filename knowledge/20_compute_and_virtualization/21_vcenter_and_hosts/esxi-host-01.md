---
id: MNE-ESXI-HOST-01
title: esxi-host-01
type: esxi_host
status: active
vendor: Fujitsu / VMware
version: ESXi 7.0
site: HQ
owner: SysAdmin-Team
criticality: critical
environment: production
last_review: '2026-07-24'
tags:
- ministry/vmware/esxi
aliases:
- MNE-ESXI-HOST-01
source: Canonical Audit
trust_tier: 3
last_verified: '2026-07-27'
related_entities: []
---
# esxi-host-01

Context: [[index-vmware]] | Server: [[vcenter-main]]

## Hardware Baseline
- **Management IP:** 172.23.69.41
- **SAN FC Switch Uplink:** [[fc-sw-fujitsu-01]]
- **Cisco Core Switch Trunk:** [[sw-cisco-core-01]]

## Hosted Virtual Machine Workloads
- [[exch-srv-01]]
- [[srv-linux-abrs-01]]
- [[ad-dc-01]]
- [[sccm-srv-01]]
