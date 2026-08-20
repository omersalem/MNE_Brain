---
id: "fw-fortigate-tubas-01"
name: "Tubas Regional Branch Firewall (FortiGate)"
category: "network"
aliases: ["tubas-firewall", "fw-tubas", "10.201.18.1", "tubas-branch"]
hostname: "fw-fortigate-tubas-01"
fqdn: "fw-fortigate-tubas-01.mne.gov.ps"
ip: "10.201.18.1"
vlan: "18"
services: ["firewall", "ipsec-vpn", "branch-routing", "nat"]
owner: "Network & Security Operations Team"
related_entities: ["fw-fortigate-hq-01", "sw-cisco-tubas-01"]
knowledge_status: "unverified"
source: "legacy_release_2_import"
last_verified: null
freshness_ttl_hours: 720
---

# Canonical Facts — Tubas Regional Branch Firewall (FortiGate)

> **Entity ID:** `fw-fortigate-tubas-01`
> **Trust Level:** Level 3 (Canonical Vault Fact)
> **Last Verified:** 2026-08-01T12:00:00Z

## 🛡️ Tubas Branch Security Details
- **Hostname:** `fw-fortigate-tubas-01`
- **Gateway IP:** `10.201.18.1`
- **Subnet:** `10.201.18.0/24` (Tubas Regional Directorate)
- **Switch IP:** `10.201.18.2` (sw-cisco-tubas-01)
- **IPSec Tunnel:** Connected to HQ FortiGate (`172.23.19.1`) via WAN
