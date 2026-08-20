---
id: "fw-fortigate-ramallah-01"
name: "Ramallah Regional Branch Firewall (FortiGate)"
category: "network"
aliases: ["ramallah-firewall", "fw-ramallah", "10.100.25.1", "ramallah-branch"]
hostname: "fw-fortigate-ramallah-01"
fqdn: "fw-fortigate-ramallah-01.mne.gov.ps"
ip: "10.100.25.1"
vlan: "25"
services: ["firewall", "ipsec-vpn", "branch-routing", "nat"]
owner: "Network & Security Operations Team"
related_entities: ["fw-fortigate-hq-01", "sw-cisco-ramallah-01"]
knowledge_status: "unverified"
source: "legacy_release_2_import"
last_verified: null
freshness_ttl_hours: 720
---

# Canonical Facts — Ramallah Regional Branch Firewall (FortiGate)

> **Entity ID:** `fw-fortigate-ramallah-01`
> **Trust Level:** Level 3 (Canonical Vault Fact)
> **Last Verified:** 2026-08-01T12:00:00Z

## 🛡️ Ramallah Regional Branch Details
- **Hostname:** `fw-fortigate-ramallah-01`
- **Gateway IP:** `10.100.25.1`
- **Subnet:** `10.100.25.0/24` (Ramallah Regional Directorate)
- **Switch IP:** `10.100.25.2` (sw-cisco-ramallah-01)
- **IPSec Tunnel:** Connected to HQ FortiGate (`172.23.19.1`) via WAN
