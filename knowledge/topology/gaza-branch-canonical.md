---
id: "fw-fortigate-gaza-01"
name: "Gaza Regional Branch Firewall (FortiGate)"
category: "network"
aliases: ["gaza-firewall", "fw-gaza", "10.211.18.1", "gaza-branch"]
hostname: "fw-fortigate-gaza-01"
fqdn: "fw-fortigate-gaza-01.mne.gov.ps"
ip: "10.211.18.1"
vlan: "18"
services: ["firewall", "ipsec-vpn", "branch-routing", "nat"]
owner: "Network & Security Operations Team"
related_entities: ["fw-fortigate-hq-01", "sw-cisco-gaza-01"]
knowledge_status: "unverified"
source: "legacy_release_2_import"
last_verified: null
freshness_ttl_hours: 720
---

# Canonical Facts — Gaza Regional Branch Firewall (FortiGate)

> **Entity ID:** `fw-fortigate-gaza-01`
> **Trust Level:** Level 3 (Canonical Vault Fact)
> **Last Verified:** 2026-08-01T12:00:00Z

## 🛡️ Gaza Branch Security Details
- **Hostname:** `fw-fortigate-gaza-01`
- **Gateway IP:** `10.211.18.1`
- **Subnet:** `10.211.18.0/24` (Gaza Regional Directorate)
- **Switch IP:** `10.211.18.2` (sw-cisco-gaza-01)
- **IPSec Tunnel:** Connected to HQ FortiGate (`172.23.70.4` / `172.23.13.201`) via WAN
