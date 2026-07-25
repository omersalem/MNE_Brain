---
id: "MNE-TMPL-ESXI"
title: "ESXi Host Template"
type: "esxi_host"
status: "active"
vendor: "Fujitsu / VMware"
version: "ESXi 7.0 / 8.0"
site: "HQ"
owner: "SysAdmin-Team"
criticality: "critical"
environment: "production"
last_review: "YYYY-MM-DD"
tags:
  - ministry/vmware/esxi
---

# {{title}}

Context: [[index-vmware]] | Server: [[vcenter-main]]

## Physical Hardware Baseline
- **Management IP:** 
- **CPU / RAM Sizing:** 
- **FC HBAs Connected To:** [[fc-sw-fujitsu-01]]

## Hosted Virtual Machines
- [[exch-srv-01]]
- [[srv-linux-abrs-01]]
