---
id: "fw-fortigate-hebron-01"
name: "Hebron Regional Branch Firewall (FortiGate)"
category: "network"
aliases: ["hebron-firewall", "fw-hebron", "FW-MNE-Hebron", "10.40.18.1", "hebron-branch"]
hostname: "FW-MNE-Hebron"
fqdn: "fw-mne-hebron.mne.gov.ps"
ip: "10.40.18.1"
vlan: "18"
services: ["firewall", "ipsec-vpn", "branch-routing", "nat"]
owner: "Network & Security Operations Team"
related_entities: ["fw-fortigate-hq-01", "sw-cisco-hebron-01"]
knowledge_status: "unverified"
source: "docs/company_docs/Ministry_Manual/BRANCH_CONNECTIVITY_BASELINE.md"
last_verified: null
freshness_ttl_hours: 720
---

# Canonical Facts — Hebron Regional Branch Firewall (FortiGate)

> **Entity ID:** `fw-fortigate-hebron-01`
> **Trust Level:** Level 3 (Canonical Vault Fact)
> **Truth Status:** Documented baseline; not live-verified in Release 2

## 🛡️ Hebron Branch Security Details
- **Hostname:** `FW-MNE-Hebron`
- **Gateway IP:** `10.40.18.1`
- **Subnet:** `10.40.18.0/24` (Hebron Regional Directorate)
- **Switch IP:** `10.40.18.3` (sw-cisco-hebron-01)
- **WAN Interfaces:** wan1 `172.27.13.62/30`, wan2 `213.6.112.10/30`
- **Central Aggregation Next Hop:** `172.23.13.201` via Port 3
- **IPSec Tunnel:** Aggregated to HQ FortiGate (`172.23.70.4` / `172.23.13.201`)
