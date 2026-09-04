---
id: "sw-cisco-core-01"
name: "HQ Core Switch (Cisco Catalyst 9500 Stack)"
category: "network"
aliases: ["cisco", "sw-cisco", "core-switch", "main core switch", "CoreSwitch1", "172.23.70.254"]
hostname: "CoreSwitch1"
fqdn: "CoreSwitch1.mne.gov.ps"
ip: "172.23.70.254"
vlan: "70"
services: ["switching", "campus-aggregation", "trunking", "40g-uplink"]
owner: "Network Infrastructure Team"
related_entities: ["fw-fortigate-hq-01", "sw-cisco-floor-1", "sw-cisco-floor-2"]
knowledge_status: "unverified"
source: "legacy_release_2_import"
last_verified: null
freshness_ttl_hours: 720
---

# Canonical Facts — Cisco Core Switch (CoreSwitch1)

> **Entity ID:** `sw-cisco-core-01`  
> **Trust Level:** Level 3 (Canonical Vault Fact)  
> **Last Verified:** 2026-07-30T10:00:00Z  

---

## 🏛️ Device Identity & Network Details
- **Hostname:** `CoreSwitch1`
- **Management IP:** `172.23.70.254` (VLAN 70 Network Management)
- **Model:** Cisco Catalyst 9500 Stack
- **Role:** Campus Aggregation Switch (Basement through Floor 6)

---

## 🔌 Interface Topology & Links
- **Po44 (40G QSFP):** Campus Uplink to Fujitsu Core (0/44) — Link UP
- **Twe 1/0/1–9:** Floor Switch Downlinks (Floor 1 through 6, GND, B1, Khadamat) — Link UP
- **Twe 1/0/12 & 2/0/12:** WAF Trunk to F5 BIG-IP (Ports 1.1 & 1.2) — Link UP

