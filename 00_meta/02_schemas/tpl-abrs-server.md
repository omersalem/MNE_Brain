---
id: "MNE-TMPL-ABRS-SRV"
title: "ABRS Server Template"
type: "abrs_server"
status: "active"
os: "Linux / Ubuntu 22.04"
site: "HQ"
owner: "AppDev-Team"
criticality: "critical"
environment: "production"
last_review: "YYYY-MM-DD"
tags:
  - ministry/compute/abrs
---

# {{title}}

Context: [[index-linux]] | Site: [[site-hq]]

## Application Overview
- **System Name:** Automated Business/Registry System (ABRS)
- **Server IP:** 

## Service Stack & Dependencies
- **Published VIP:** [[f5-vip-public-98]]
- **Firewall Policy:** [[fw-fortigate-hq-01]]
- **VMware Host:** [[esxi-host-01]]
- **Database Server:** [[srv-linux-db-01]]
