---
id: "MNE-TMPL-F5"
title: "F5 BIG-IP WAF Template"
type: "f5_object"
status: "active"
vendor: "F5 Networks"
model: "BIG-IP Virtual Edition / iSeries"
version: "TMOS 16.1"
site: "HQ"
owner: "SecOps-Team"
criticality: "critical"
environment: "production"
last_review: "YYYY-MM-DD"
tags:
  - ministry/security/f5-waf
---

# {{title}}

Context: [[index-network-and-security]] | Site: [[site-hq]]

## Virtual Server Details
- **VIP IP Address:** 
- **Port / Protocol:** 443 / HTTPS
- **SSL Offloading Cert:** [[cert-wildcard-mne]]

## Backend Pool & Health Monitors
- **Pool Target:** [[f5-pool-abrs]]
- **Health Monitor:** HTTPS GET /health check

## Attached Security Policies
- **WAF Policy:** [[f5-waf-policy-main]]

## Upstream & Downstream Dependencies
- **Perimeter Firewall:** [[fw-fortigate-hq-01]]
- **Backend Application Server:** [[srv-linux-abrs-01]]
