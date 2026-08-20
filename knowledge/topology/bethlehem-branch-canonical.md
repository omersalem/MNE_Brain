---
id: "fw-fortigate-bethlehem-01"
name: "Bethlehem Regional Branch Firewall (FortiGate)"
category: "network"
aliases: ["bethlehem-firewall", "fw-bethlehem", "10.70.18.1", "bethlehem-branch"]
hostname: "fw-fortigate-bethlehem-01"
fqdn: "fw-fortigate-bethlehem-01.mne.gov.ps"
ip: "10.70.18.1"
vlan: "18"
services: ["firewall", "ipsec-vpn", "branch-routing", "nat"]
owner: "Network & Security Operations Team"
related_entities: ["fw-fortigate-hq-01", "sw-cisco-bethlehem-01"]
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
- **Hostname:** `fw-fortigate-bethlehem-01`
- **Gateway IP:** `10.70.18.1`
- **Subnet:** `10.70.18.0/24` (Bethlehem Regional Directorate)
- **Switch IP:** `10.70.18.2` (sw-cisco-bethlehem-01)
- **IPSec Tunnel:** Connected to HQ FortiGate (`172.23.19.1`) via WAN
