---
id: "fw-fortigate-qalqilya-01"
name: "Qalqilya Regional Branch Firewall (FortiGate)"
category: "network"
aliases: ["qalqilya-firewall", "fw-qalqilya", "10.131.18.1", "qalqilya-branch"]
hostname: "fw-fortigate-qalqilya-01"
fqdn: "fw-fortigate-qalqilya-01.mne.gov.ps"
ip: "10.131.18.1"
vlan: "18"
services: ["firewall", "ipsec-vpn", "branch-routing", "nat"]
owner: "Network & Security Operations Team"
related_entities: ["fw-fortigate-hq-01", "sw-cisco-qalqilya-01"]
knowledge_status: "unverified"
source: "legacy_release_2_import"
last_verified: null
freshness_ttl_hours: 720
---

# Canonical Facts — Qalqilya Regional Branch Firewall (FortiGate)

> **Entity ID:** `fw-fortigate-qalqilya-01`
> **Trust Level:** Level 3 (Canonical Vault Fact)
> **Last Verified:** 2026-08-01T12:00:00Z

## 🛡️ Qalqilya Branch Security Details
- **Hostname:** `fw-fortigate-qalqilya-01`
- **Gateway IP:** `10.131.18.1`
- **Subnet:** `10.131.18.0/24` (Qalqilya Regional Directorate)
- **Switch IP:** `10.131.18.2` (sw-cisco-qalqilya-01)
- **IPSec Tunnel:** Connected to HQ FortiGate (`172.23.19.1`) via WAN
