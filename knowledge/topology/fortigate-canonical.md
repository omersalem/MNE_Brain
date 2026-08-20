---
id: "fw-fortigate-hq-01"
name: "HQ Core Firewall (FortiGate)"
category: "network"
aliases: ["fortigate", "fw-fortigate", "fortigate-01", "172.23.19.1", "hq-firewall"]
hostname: "fw-fortigate-hq-01"
fqdn: "fw-fortigate-hq-01.mne.gov.ps"
ip: "172.23.19.1"
vlan: "19"
services: ["firewall", "ipsec-vpn", "nat", "routing"]
owner: "Network Infrastructure Team"
related_entities: ["sw-cisco-core-01", "vc-vmware-hq-01"]
knowledge_status: "unverified"
source: "legacy_release_2_import"
last_verified: null
freshness_ttl_hours: 720
---

# Canonical Facts — FortiGate Core Firewall

> **Entity ID:** `fw-fortigate-hq-01`  
> **Trust Level:** Level 3 (Canonical Vault Fact)  
> **Last Verified:** 2026-07-30T10:00:00Z  

---

## 🏛️ Device Identity & Network Details
- **Hostname:** `fw-fortigate-hq-01`
- **Management IP:** `172.23.19.1`
- **Model:** FortiGate-100E
- **Firmware:** FortiOS v7.0.5 build0304
- **Role:** Primary Enterprise Edge & Branch Firewall

---

## 🔌 Interface Topology
- **port1:** WAN Uplink (172.23.19.1/24) — Link UP
- **port2:** Secondary ISP WAN — Link DOWN
- **port3:** Internal LAN Backbone — Link UP
