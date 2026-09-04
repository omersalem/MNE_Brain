---
id: "fw-fortigate-hq-01"
name: "HQ Core Firewall (FortiGate 601E)"
category: "network"
aliases: ["fortigate", "fw-fortigate-hq-01", "fortigate-hq", "fg-mne-b", "172.23.13.201", "hq-firewall", "FG-MNE-B"]
hostname: "FG-MNE-B"
fqdn: "FG-MNE-B.mne.gov.ps"
ip: "172.23.13.201"
vlan: "13"
services: ["firewall", "ipsec-vpn", "nat", "routing", "ssl-vpn", "branch-interconnect"]
owner: "Network Infrastructure Team"
related_entities: ["sw-cisco-core-01", "vc-vmware-hq-01", "ftd-cisco-hq-01"]
knowledge_status: "unverified"
source: "legacy_release_2_import"
last_verified: null
freshness_ttl_hours: 720
---

# Canonical Facts — FortiGate Core Firewall (FG-MNE-B)

> **Entity ID:** `fw-fortigate-hq-01`  
> **Trust Level:** Level 3 (Canonical Vault Fact)  
> **Last Verified:** 2026-07-30T10:00:00Z  

---

## 🏛️ Device Identity & Network Details
- **Device Name:** `FG-MNE-B`
- **Management IP:** `172.23.70.4` (VLAN 70 Network Management)
- **Internal Gateway IP:** `10.11.12.1`
- **Model:** FortiGate 601E
- **Firmware:** FortiOS 7.4.x
- **Role:** Primary Enterprise Edge, SSL-VPN Gateway, Default Gateway for User LANs, and Branch Hub

---

## 🔌 Interface Topology
- **port1:** Legacy ISP / Gov VPN Uplink — Link UP
- **port2:** Primary Internet WAN (ISP Gateway, default route) — Link UP
- **port3:** Branch MPLS Router Interconnect (172.23.13.201 next hop) — Link UP
- **x1:** 10G SFP+ User LAN Trunk to Fujitsu Core (0/47) — Link UP
- **x2:** 10G SFP+ Server Transit VLAN 200 to Fujitsu Core (0/40) — Link UP

