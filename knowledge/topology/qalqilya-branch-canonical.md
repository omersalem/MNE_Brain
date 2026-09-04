---
id: "fw-fortigate-qalqilya-01"
name: "Qalqilya Regional Branch Firewall (FortiGate)"
category: "network"
aliases: ["qalqilya-firewall", "fw-qalqilya", "10.180.18.1", "qalqilya-branch", "FW-MNE-Qalqilyah"]
hostname: "FW-MNE-Qalqilyah"
fqdn: "FW-MNE-Qalqilyah.mne.gov.ps"
ip: "10.180.18.1"
vlan: "18"
services: ["firewall", "ipsec-vpn", "branch-routing", "nat"]
owner: "Network & Security Operations Team"
related_entities: ["fw-fortigate-hq-01"]
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
- **Hostname:** `FW-MNE-Qalqilyah`
- **Gateway IP:** `10.180.18.1`
- **Subnet:** `10.180.18.0/24` (Qalqilya Regional Directorate)
- **Switch IP:** `10.180.18.3` (Branch Switch)
- **Router IP:** `10.180.18.2` (Branch Router)
- **WAN Links:**
  - **wan1:** `172.27.13.46/30` (Central Interconnect)
  - **wan2:** `213.6.192.170/30` (Public Internet WAN)
  - **internal:** `10.180.18.1/24` (Local Branch LAN)

