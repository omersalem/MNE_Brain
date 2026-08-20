---
id: "fw-fortigate-tulkarm-01"
name: "Tulkarm Regional Branch Firewall (FortiGate)"
category: "network"
aliases: ["tulkarm-firewall", "fw-tulkarm", "10.110.19.1", "tulkarm-branch"]
hostname: "fw-fortigate-tulkarm-01"
fqdn: "fw-fortigate-tulkarm-01.mne.gov.ps"
ip: "10.110.19.1"
vlan: "19"
services: ["firewall", "ipsec-vpn", "branch-routing", "nat"]
owner: "Network & Security Operations Team"
related_entities: ["fw-fortigate-hq-01", "sw-cisco-tulkarm-01"]
knowledge_status: "unverified"
source: "legacy_release_2_import"
last_verified: null
freshness_ttl_hours: 720
---

# Canonical Facts — Tulkarm Regional Branch Firewall (FortiGate)

> **Entity ID:** `fw-fortigate-tulkarm-01`
> **Trust Level:** Level 3 (Canonical Vault Fact)
> **Last Verified:** 2026-08-01T12:00:00Z

## 🛡️ Tulkarm Branch Security Details
- **Hostname:** `fw-fortigate-tulkarm-01`
- **Gateway IP:** `10.110.19.1`
- **Subnet:** `10.110.19.0/24` (Tulkarm Regional Directorate)
- **Switch IP:** `10.110.19.2` (sw-cisco-tulkarm-01)
- **IPSec Tunnel:** Connected to HQ FortiGate (`172.23.19.1`) via WAN
