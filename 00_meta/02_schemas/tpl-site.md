---
id: "MNE-TMPL-SITE"
title: "Site Template"
type: "site"
status: "draft|active"
owner: "Network-Team"
criticality: "high"
environment: "production"
last_review: "YYYY-MM-DD"
tags:
  - ministry/site
---

# {{title}}

Context: [[master-dashboard]] | Parent: [[index-network-and-security]]

## Overview & Location
- **Site Type:** Headquarters / Branch Office
- **Physical Location:** 
- **Primary Contact:** 

## Topology & Connected Infrastructure
- **Primary WAN Router:** [[rtr-cisco-wan-01]]
- **Edge Firewall:** [[fw-fortigate-hq-01]]
- **Core Switch:** [[sw-cisco-core-01]]

## Local Subnets & Networks
- [[subnet-mgmt]]
- [[subnet-users]]

## Related Runbooks & Incidents
- [[sop-site-failover]]
- [[rca-site-outage]]
