---
id: "fw-fortigate-jericho-01"
name: "Jericho Regional Branch Firewall (FortiGate)"
category: "network"
aliases: ["jericho-firewall", "fw-jericho", "10.180.18.1", "jericho-branch"]
hostname: "fw-fortigate-jericho-01"
fqdn: "fw-fortigate-jericho-01.mne.gov.ps"
ip: "10.180.18.1"
vlan: "18"
services: ["firewall", "ipsec-vpn", "branch-routing", "nat"]
owner: "Network & Security Operations Team"
related_entities: ["fw-fortigate-hq-01", "sw-cisco-jericho-01"]
knowledge_status: "unverified"
source: "legacy_release_2_import"
last_verified: null
freshness_ttl_hours: 720
---

# Canonical Facts — Jericho Regional Branch Firewall (FortiGate)

> **Entity ID:** `fw-fortigate-jericho-01`
> **Trust Level:** Level 3 (Canonical Vault Fact)
> **Last Verified:** 2026-08-01T12:00:00Z

## 🛡️ Jericho Branch Security Details
- **Hostname:** `fw-fortigate-jericho-01`
- **Gateway IP:** `10.180.18.1`
- **Subnet:** `10.180.18.0/24` (Jericho Regional Directorate)
- **Switch IP:** `10.180.18.2` (sw-cisco-jericho-01)
- **IPSec Tunnel:** Connected to HQ FortiGate (`172.23.19.1`) via WAN
