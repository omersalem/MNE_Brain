---
id: "fw-fortigate-tulkarm-01"
name: "Tulkarm Regional Branch Firewall (FortiGate)"
category: "network"
aliases: ["tulkarm-firewall", "fw-tulkarm", "10.165.18.1", "tulkarm-branch"]
hostname: "fw-fortigate-tulkarm-01"
fqdn: "fw-fortigate-tulkarm-01.mne.gov.ps"
ip: "10.165.18.1"
vlan: ""
services: ["firewall", "ipsec-vpn", "branch-routing", "nat"]
owner: "Network & Security Operations Team"
related_entities: ["fw-fortigate-hq-01", "rtr-tulkarm-01", "sw-cisco-tulkarm-01"]
knowledge_status: "unverified"
source: "MNE_Infrastructure/BRANCH_CONNECTIVITY_BASELINE.md"
last_verified: null
freshness_ttl_hours: 720
---

# Canonical Facts — Tulkarm Regional Branch Firewall (FortiGate)

> **Entity ID:** `fw-fortigate-tulkarm-01`
> **Trust Level:** Level 3 (Canonical Vault Fact)
> **Last Verified:** 2026-08-01T12:00:00Z

## 🛡️ Tulkarm Branch Security Details
- **Hostname:** `fw-fortigate-tulkarm-01`
- **Gateway IP:** `10.165.18.1`
- **Subnet:** `10.165.18.0/24` (Tulkarm Regional Directorate)
- **Switch IP:** `10.165.18.3` (`sw-cisco-tulkarm-01` / `sw-access-tulkarm`)
- **Central Aggregation Next Hop:** `172.23.13.201` (documented baseline; not live-verified in this record)
