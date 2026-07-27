---
id: MNE-SW-CISCO-CORE-01
title: CoreSwitch1 (Cisco 9500 Stack)
type: cisco_core_switch
status: active
vendor: Cisco
model: Catalyst 9500 Stack
mgmt_ip: 172.23.70.254
site: HQ
owner: Network-Team
criticality: critical
environment: production
last_review: '2026-07-24'
tags:
- ministry/cisco/core-switch
aliases:
- MNE-SW-CISCO-CORE-01
source: Canonical Audit
trust_tier: 3
last_verified: '2026-07-27'
related_entities: []
---
# CoreSwitch1 (Cisco Catalyst 9500 Stack)

Context: [[master-dashboard]] | Parent: [[index-network-and-security]]

## Overview
- **Device Hostname:** CoreSwitch1
- **Management IP:** `172.23.70.254`
- **Role:** Campus Distribution & Floor Aggregation (Basement through Floor 6)

## Uplinks & Connectivity
- **40G Fiber Uplinks:** Connected to Fujitsu Core Fabric [[sw-fujitsu-core-02]]
- **Floor Switches:** Downstream trunks to Floor Access Switches [[sw-cisco-access-01]]

## Served VLANs
- VLAN 19 (Floor 1 Staff: `172.23.19.0/24`)
- VLAN 21 (Floor 2 Staff: `172.23.21.0/24`)
- VLAN 23 (Floor 3 Staff: `172.23.23.0/24`)
- VLAN 42 (Printers: `172.23.42.0/24`)
