---
id: "MNE-SW-FUJ-CORE-02"
title: "MNE-CoreSw2 (Fujitsu Core)"
type: "fujitsu_core_switch"
status: "active"
vendor: "Fujitsu"
model: "PSWITCH 2048P"
mgmt_ip: "172.23.70.71"
site: "HQ"
owner: "Network-Team"
criticality: "critical"
environment: "production"
last_review: "2026-07-24"
tags:
  - ministry/fujitsu/core-switch
---

# MNE-CoreSw2 (Fujitsu Core Switch)

Context: [[master-dashboard]] | Parent: [[index-network-and-security]]

## System Baseline
- **Device Hostname:** MNE-CoreSw2
- **Management IP:** `172.23.70.71`
- **Role:** Central Fabric Backbone — Interconnects Firewalls, Campus Aggregation, and Server Zones

## Cabling & Critical Uplinks
- **Port `0/47` (10G):** Connected to FortiGate [[fw-fortigate-hq-01]] Port `x1` (Trunk: User LANs)
- **Port `0/40` (10G):** Connected to FortiGate [[fw-fortigate-hq-01]] Port `x2` (Server Transit VLAN 200)
- **Port `0/39` (10G):** Connected to Cisco FTD [[cisco-ftd-01]] Outside Port (`Po1`)
- **Port `0/46` (10G):** Connected to Cisco FTD [[cisco-ftd-01]] Inside Port (`Po2`)
- **40G Uplinks:** Connected to Cisco Core Stack [[sw-cisco-core-01]]

## Connected Assets
- [[fw-fortigate-hq-01]]
- [[sw-cisco-core-01]]
- [[cisco-ftd-01]]
- [[f5-vip-public-98]]
