---
id: "MNE-SITE-HQ"
title: "Ministry Headquarters (HQ)"
type: "site"
status: "active"
owner: "Network-Team"
criticality: "critical"
environment: "production"
last_review: "2026-07-24"
tags:
  - ministry/site/hq
---

# Ministry Headquarters (HQ)

Context: [[master-dashboard]] | Parent: [[index-network-and-security]]

## Site Overview
- **Location:** Central Ministry Campus
- **Role:** Primary Data Center & Headquarters Operational Node

## Primary Connected Hardware
- **Perimeter Firewall:** [[fw-fortigate-hq-01]]
- **Core Switch:** [[sw-cisco-core-01]]
- **WAN Router:** [[rtr-cisco-wan-01]]
- **WAF Appliance:** [[f5-vip-public-98]]
- **Virtualization Datacenter:** [[vcenter-main]]

## Connected Sites
- [[site-branch-north]]
