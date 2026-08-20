---
id: "fw-fortigate-hebron-01"
name: "Hebron Regional Branch Firewall (FortiGate)"
category: "network"
aliases: ["hebron-firewall", "fw-hebron", "10.40.18.1", "hebron-branch"]
hostname: "fw-fortigate-hebron-01"
fqdn: "fw-fortigate-hebron-01.mne.gov.ps"
ip: "10.40.18.1"
vlan: "18"
services: ["firewall", "ipsec-vpn", "branch-routing", "nat"]
owner: "Network & Security Operations Team"
related_entities: ["fw-fortigate-hq-01", "sw-cisco-hebron-01"]
knowledge_status: "unverified"
source: "legacy_release_2_import"
last_verified: null
freshness_ttl_hours: 720
---

# Canonical Facts — Hebron Regional Branch Firewall (FortiGate)

> **Entity ID:** `fw-fortigate-hebron-01`
> **Trust Level:** Level 3 (Canonical Vault Fact)
> **Last Verified:** 2026-08-01T12:00:00Z

## 🛡️ Hebron Branch Security Details
- **Hostname:** `fw-fortigate-hebron-01`
- **Gateway IP:** `10.40.18.1`
- **Subnet:** `10.40.18.0/24` (Hebron Regional Directorate)
- **Switch IP:** `10.40.18.2` (sw-cisco-hebron-01)
- **IPSec Tunnel:** Connected to HQ FortiGate (`172.23.19.1`) via WAN
