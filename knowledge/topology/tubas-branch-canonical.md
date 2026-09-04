---
id: "fw-fortigate-tubas-01"
name: "Tubas Regional Branch Firewall (FortiGate)"
category: "network"
aliases: ["tubas-firewall", "fw-tubas", "FW-MNE-Tubas", "10.230.18.1", "tubas-branch"]
hostname: "FW-MNE-Tubas"
fqdn: "fw-mne-tubas.mne.gov.ps"
ip: "10.230.18.1"
vlan: "18"
services: ["firewall", "ipsec-vpn", "branch-routing", "nat"]
owner: "Network & Security Operations Team"
related_entities: ["fw-fortigate-hq-01", "sw-cisco-tubas-01"]
knowledge_status: "unverified"
source: "docs/company_docs/Ministry_Manual/BRANCH_CONNECTIVITY_BASELINE.md"
last_verified: null
freshness_ttl_hours: 720
---

# Canonical Facts — Tubas Regional Branch Firewall (FortiGate)

> **Entity ID:** `fw-fortigate-tubas-01`
> **Trust Level:** Level 3 (Canonical Vault Fact)
> **Truth Status:** Documented baseline; not live-verified in Release 2

## 🛡️ Tubas Branch Security Details
- **Hostname:** `FW-MNE-Tubas`
- **Gateway IP:** `10.230.18.1`
- **Subnet:** `10.230.18.0/24` (Tubas Regional Directorate)
- **Switch IP:** `10.230.18.3` (sw-cisco-tubas-01 / TubasSW)
- **WAN Interfaces:** wan1 `172.27.13.18/30`, wan2 `213.6.192.150/30`
- **Central Aggregation Next Hop:** `172.23.13.201` via Port 3
- **IPSec Tunnel:** Aggregated to HQ FortiGate (`172.23.70.4` / `172.23.13.201`)
