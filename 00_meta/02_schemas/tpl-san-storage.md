---
id: "MNE-TMPL-SAN"
title: "Fujitsu SAN Storage Array Template"
type: "fujitsu_san"
status: "active"
vendor: "Fujitsu"
model: "ETERNUS DX200"
site: "HQ"
owner: "SysAdmin-Team"
criticality: "critical"
environment: "production"
last_review: "YYYY-MM-DD"
tags:
  - ministry/storage/fujitsu-san
---

# {{title}}

Context: [[index-storage]] | Site: [[site-hq]]

## System Baseline
- **Management IP:** 172.23.68.20
- **Total Storage Capacity:** 

## FC Switch Interconnects
- [[fc-sw-fujitsu-01]]

## Storage LUNs & VMware Datastores
- Datastore-SAN-01 -> [[esxi-host-01]]
