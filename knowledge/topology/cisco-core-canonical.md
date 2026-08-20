---
id: "sw-cisco-core-01"
name: "HQ Core Switch (Cisco IOS-XE)"
category: "network"
aliases: ["cisco", "sw-cisco", "core-switch", "172.23.19.2"]
hostname: "sw-cisco-core-01"
fqdn: "sw-cisco-core-01.mne.gov.ps"
ip: "172.23.19.2"
vlan: "19"
services: ["switching", "vlan-routing", "trunking"]
owner: "Network Infrastructure Team"
related_entities: ["fw-fortigate-hq-01"]
knowledge_status: "unverified"
source: "legacy_release_2_import"
last_verified: null
freshness_ttl_hours: 720
---

# Canonical Facts — Cisco Core Switch

> **Entity ID:** `sw-cisco-core-01`  
> **Trust Level:** Level 3 (Canonical Vault Fact)  
> **Last Verified:** 2026-07-30T10:00:00Z  

---

## 🏛️ Device Identity & Network Details
- **Hostname:** `sw-cisco-core-01`
- **Management IP:** `172.23.19.2`
- **Model:** Cisco Catalyst 9300
- **IOS-XE Version:** 17.06.03
- **Role:** HQ Core Distribution Switch

---

## 🔌 Interface Topology
- **GigabitEthernet0/0/1:** Core Gateway (172.23.19.2/24) — Link UP
- **GigabitEthernet0/0/2:** Access Switch Trunk — Link DOWN
