---
id: "fw-fortigate-ramallah-01"
name: "Ramallah Regional Branch Firewall (FortiGate)"
category: "network"
aliases: ["ramallah-firewall", "fw-ramallah", "FW-MNE-Ramallah-Gold", "10.110.19.1", "ramallah-branch", "ramallah-gold"]
hostname: "FW-MNE-Ramallah-Gold"
fqdn: "fw-mne-ramallah-gold.mne.gov.ps"
ip: "10.110.19.1"
vlan: "19"
services: ["firewall", "ipsec-vpn", "branch-routing", "nat"]
owner: "Network & Security Operations Team"
related_entities: ["fw-fortigate-hq-01", "sw-cisco-ramallah-01"]
knowledge_status: "unverified"
source: "docs/company_docs/Ministry_Manual/BRANCH_CONNECTIVITY_BASELINE.md"
last_verified: null
freshness_ttl_hours: 720
---

# Canonical Facts — Ramallah Regional Branch Firewall (FortiGate)

> **Entity ID:** `fw-fortigate-ramallah-01`
> **Trust Level:** Level 3 (Canonical Vault Fact)
> **Truth Status:** Documented baseline; not live-verified in Release 2

## 🛡️ Ramallah Regional Branch Details
- **Hostname:** `FW-MNE-Ramallah-Gold`
- **Gateway IP:** `10.110.19.1`
- **Subnet:** `10.110.19.0/24` (Ramallah Gold Directorate)
- **Switch IP:** `10.110.19.3` (sw-cisco-ramallah-01)
- **Central Aggregation Next Hop:** `172.23.13.201` via Port 3
- **IPSec Tunnel:** Aggregated to HQ FortiGate (`172.23.70.4` / `172.23.13.201`)
