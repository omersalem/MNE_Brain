---
id: MNE-RTR-NABLUS-01
title: Nablus Branch Router (rtr-nablus-01)
type: cisco_router
status: live_verified
vendor: Cisco
model: Branch Router
os: Cisco IOS
site: Nablus (نابلس)
owner: Network-Team
criticality: high
environment: production
last_review: '2026-07-27'
tags:
- ministry/cisco/router
- ministry/site/nablus
aliases:
- MNE-RTR-NABLUS-01
- rtr-nablus-01
source: Live Verification
trust_tier: 5
last_verified: '2026-07-27'
related_entities: []
---
# Nablus Branch Router (rtr-nablus-01)

Context: [[index-network-and-security]] | Site: [[site-hq]]

## System Properties
- **Branch Office:** Nablus (نابلس)
- **Management IP:** `10.131.18.2`
- **Subnet Allocation:** `10.131.18.0/24`
- **Management Protocol:** Telnet (Port 23)
- **Authentication Scheme:** Line Password (`vivajaradatos`) + Enable Password (`nabulsi`) [No Username]
- **Authentication Env Var:** `MNE_ROUTER_NABLUS_LINE_PASSWORD` / `MNE_ROUTER_NABLUS_ENABLE_PASSWORD`
- **Live Status:** UP / Verified
