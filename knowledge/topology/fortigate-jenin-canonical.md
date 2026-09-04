---
id: "fw-fortigate-jenin-01"
name: "Jenin Branch Firewall (FortiGate 71G)"
category: "network"
aliases: ["jenin-firewall", "fw-jenin", "fortigate-jenin", "10.201.18.1", "jenin-fw", "FW-MNE-Jenin"]
hostname: "FW-MNE-Jenin"
fqdn: "FW-MNE-Jenin.mne.gov.ps"
ip: "10.201.18.1"
vlan: "18"
services: ["firewall", "ipsec-vpn", "nat", "branch-routing"]
owner: "Network & Security Operations Team"
related_entities: ["sw-cisco-jenin-01", "fw-fortigate-hq-01", "prt-jenin-office-01"]
knowledge_status: "unverified"
source: "legacy_release_2_import"
last_verified: null
freshness_ttl_hours: 720
---

# Canonical Facts — Jenin Branch Firewall (FortiGate 71G)

> **Entity ID:** `fw-fortigate-jenin-01`
> **Trust Level:** Level 3 (Canonical Vault Fact)
> **Last Verified:** 2026-08-01T12:00:00Z

## 🛡️ Device & Network Specs
- **Hostname:** `FW-MNE-Jenin`
- **Management IP:** `10.201.18.1` (VLAN 18 Gateway)
- **Product:** FortiGate-71G (FortiOS 7.4.11 build2878)
- **Branch Location:** Jenin Branch Office (Subnet `10.201.18.0/24`)
- **WAN Links:**
  - **wan1:** `172.27.13.26/30` (Central Interconnect to HQ Port 3)
  - **wan2:** `213.6.192.118/30` (Public Internet WAN)
  - **internal:** `10.201.18.1/24` (Local Branch LAN)

