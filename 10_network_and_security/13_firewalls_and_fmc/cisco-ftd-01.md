---
id: "MNE-CISCO-FTD-01"
title: "FTD-01 (Cisco Firepower 3105)"
type: "cisco_ftd"
status: "active"
vendor: "Cisco"
model: "Firepower 3105"
mgmt_ip: "172.23.70.78"
site: "HQ"
owner: "SecOps-Team"
criticality: "critical"
environment: "production"
last_review: "2026-07-24"
tags:
  - ministry/security/cisco-ftd
---

# FTD-01 (Cisco Firepower 3105)

Context: [[index-network-and-security]] | Managed By: [[cisco-fmc-01]]

## System Overview
- **Hostname:** FTD-01
- **Management IP:** `172.23.70.78`
- **Role:** Dedicated Server Zone Firewall — Deep inspection guarding VLAN 71 (Core Servers), VLAN 75, and VLAN 79

## Interface Bindings
- **Po1 (Outside):** Connected to Fujitsu Core [[sw-fujitsu-core-02]] Port `0/39`
- **Po2 (Inside):** Connected to Fujitsu Core [[sw-fujitsu-core-02]] Port `0/46`

## Management
- Centralized Policy Control via FMC [[cisco-fmc-01]] (`172.23.70.77`)
