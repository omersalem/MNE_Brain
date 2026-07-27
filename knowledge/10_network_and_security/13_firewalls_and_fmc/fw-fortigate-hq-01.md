---
id: MNE-FW-FG-HQ-01
title: FG-MNE-B (FortiGate 601E)
type: fortigate_device
status: active
vendor: Fortinet
model: FortiGate 601E
firmware: FortiOS 7.4.x
mgmt_ip: 172.23.70.4
cluster_ip: 10.11.12.1
site: HQ
owner: SecOps-Team
criticality: critical
environment: production
last_review: '2026-07-24'
tags:
- ministry/security/fortigate
aliases:
- MNE-FW-FG-HQ-01
source: Canonical Audit
trust_tier: 3
last_verified: '2026-07-27'
related_entities: []
---
# FG-MNE-B (FortiGate 601E)

Context: [[master-dashboard]] | Parent: [[index-network-and-security]]

## Overview & Location
- **Device Name:** FG-MNE-B
- **Hardware Model:** FortiGate 601E
- **Management IP:** `172.23.70.4`
- **Internal Gateway IP:** `10.11.12.1`
- **Role:** Internet Edge, SSL-VPN Gateway, Default Gateway for User LAN VLANs (19, 21, 23, 42, 76)

## Cabling & Fabric Connectivity
- **Port `x1` (10G SFP+):** Uplinks to Fujitsu Core Switch [[sw-fujitsu-core-02]] Port `0/47` (User LAN Trunk)
- **Port `x2` (10G SFP+):** Uplinks to Fujitsu Core Switch [[sw-fujitsu-core-02]] Port `0/40` (Server Transit VLAN 200)

## Security Services & Interfaces
- **Protected User Subnets:** VLAN 19 (`172.23.19.0/24`), VLAN 21 (`172.23.21.0/24`), VLAN 23 (`172.23.23.0/24`)
- **Remote Access:** [[vpn-ssl-hq]] (`https://vpn.mne.gov.ps`)
- **Downstream Protection:** Interconnects to Cisco FTD [[cisco-ftd-01]] and F5 WAF [[f5-vip-public-98]]

## Connected Infrastructure
- Upstream Router: [[rtr-cisco-wan-01]]
- Core Fabric: [[sw-fujitsu-core-02]]
- Campus Aggregation: [[sw-cisco-core-01]]
