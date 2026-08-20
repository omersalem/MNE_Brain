---
id: "fw-fortigate-salfit-01"
name: "Salfit Regional Branch Firewall (FortiGate)"
category: "network"
aliases: ["salfit-firewall", "fw-salfit", "10.165.18.1", "salfit-branch"]
hostname: "fw-fortigate-salfit-01"
fqdn: "fw-fortigate-salfit-01.mne.gov.ps"
ip: "10.165.18.1"
vlan: "18"
services: ["firewall", "ipsec-vpn", "branch-routing", "nat"]
owner: "Network & Security Operations Team"
related_entities: ["fw-fortigate-hq-01", "sw-cisco-salfit-01"]
knowledge_status: "unverified"
source: "legacy_release_2_import"
last_verified: null
freshness_ttl_hours: 720
---

# Canonical Facts — Salfit Regional Branch Firewall (FortiGate)

> **Entity ID:** `fw-fortigate-salfit-01`
> **Trust Level:** Level 3 (Canonical Vault Fact)
> **Last Verified:** 2026-08-01T12:00:00Z

## 🛡️ Salfit Branch Security Details
- **Hostname:** `fw-fortigate-salfit-01`
- **Gateway IP:** `10.165.18.1`
- **Subnet:** `10.165.18.0/24` (Salfit Regional Directorate)
- **Switch IP:** `10.165.18.2` (sw-cisco-salfit-01)
- **IPSec Tunnel:** Connected to HQ FortiGate (`172.23.19.1`) via WAN
