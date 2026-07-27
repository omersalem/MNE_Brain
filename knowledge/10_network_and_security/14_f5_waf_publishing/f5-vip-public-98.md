---
id: MNE-F5-VIP-PUB-98
title: F5 BIG-IP r2000 (ESADAD WAF)
type: f5_object
status: active
vendor: F5
model: BIG-IP r2000
mgmt_ip: 172.23.70.89
vip_ip: 172.23.79.200
site: HQ
owner: SecOps-Team
criticality: critical
environment: production
last_review: '2026-07-24'
tags:
- ministry/security/f5-waf
aliases:
- MNE-F5-VIP-PUB-98
source: Canonical Audit
trust_tier: 3
last_verified: '2026-07-27'
related_entities: []
---
# F5 BIG-IP r2000 (WAF Publishing)

Context: [[index-network-and-security]] | Site: [[site-hq]]

## System Details
- **Management IP:** `172.23.70.89`
- **Public VIP IP:** `172.23.79.200`
- **Role:** Web Application Firewall — Protects ESADAD public portal and Ministry web applications against SQLi, XSS, and bot attacks

## Backend Server Pools
- [[srv-linux-abrs-01]] (`172.23.79.200` / Greenunit)
- [[exch-srv-01]] (`172.23.71.35`) & [[exch-srv-02]] (`172.23.71.36`)

## Upstream & Downstream Interconnects
- Perimeter Pass-Through: [[fw-fortigate-hq-01]]
- Server Zone Firewall: [[cisco-ftd-01]]
