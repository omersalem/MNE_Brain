---
id: "fw-fortigate-nablus-01"
name: "Nablus Regional Branch Firewall (FortiGate)"
category: "network"
aliases: ["nablus-firewall", "fw-nablus", "10.60.18.1", "nablus-branch"]
hostname: "fw-fortigate-nablus-01"
fqdn: "fw-fortigate-nablus-01.mne.gov.ps"
ip: "10.60.18.1"
vlan: "18"
services: ["firewall", "ipsec-vpn", "branch-routing", "nat"]
owner: "Network & Security Operations Team"
related_entities: ["fw-fortigate-hq-01", "sw-cisco-nablus-01"]
knowledge_status: "unverified"
source: "legacy_release_2_import"
last_verified: null
freshness_ttl_hours: 720
---

# Canonical Facts — Nablus Regional Branch Firewall (FortiGate)

> **Entity ID:** `fw-fortigate-nablus-01`
> **Trust Level:** Level 3 (Canonical Vault Fact)
> **Last Verified:** 2026-08-01T12:00:00Z

## 🛡️ Nablus Branch Security Details
- **Hostname:** `fw-fortigate-nablus-01`
- **Gateway IP:** `10.60.18.1`
- **Subnet:** `10.60.18.0/24` (Nablus Regional Directorate)
- **Switch IP:** `10.60.18.2` (sw-cisco-nablus-01)
- **IPSec Tunnel:** Connected to HQ FortiGate (`172.23.19.1`) via WAN
