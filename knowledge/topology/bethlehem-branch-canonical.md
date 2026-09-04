---
id: "fw-fortigate-bethlehem-01"
name: "Bethlehem Regional Branch Firewall (FortiGate)"
category: "network"
aliases: ["bethlehem-firewall", "fw-bethlehem", "10.60.18.1", "bethlehem-branch", "FW-MNE-Bethlahem"]
hostname: "FW-MNE-Bethlahem"
fqdn: "FW-MNE-Bethlahem.mne.gov.ps"
ip: "10.60.18.1"
vlan: "18"
services: ["firewall", "ipsec-vpn", "branch-routing", "nat"]
owner: "Network & Security Operations Team"
related_entities: ["fw-fortigate-hq-01"]
knowledge_status: "unverified"
source: "legacy_release_2_import"
last_verified: null
freshness_ttl_hours: 720
---

# Canonical Facts — Bethlehem Regional Branch Firewall (FortiGate)

> **Entity ID:** `fw-fortigate-bethlehem-01`
> **Trust Level:** Level 3 (Canonical Vault Fact)
> **Last Verified:** 2026-08-01T12:00:00Z

## 🛡️ Bethlehem Branch Security Details
- **Hostname:** `FW-MNE-Bethlahem`
- **Gateway IP:** `10.60.18.1`
- **Subnet:** `10.60.18.0/24` (Bethlehem Regional Directorate)
- **Switch IP:** `10.60.18.3` (Branch Switch)
- **Router IP:** `10.60.18.2` (Branch Router)
- **WAN Links:**
  - **wan1:** `172.27.13.14/24` (Central Interconnect)
  - **wan2:** `213.6.108.18/30` (Public Internet WAN)
  - **internal:** `10.60.18.1/24` (Local Branch LAN)

