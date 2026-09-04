---
id: "sw-cisco-tulkarm-01"
name: "Tulkarm Branch Access Switch"
category: "network"
aliases: ["tulkarm-switch", "tulkarm switch", "tulkarm access switch", "sw-tulkarm", "sw-access-tulkarm", "10.165.18.3"]
hostname: "sw-access-tulkarm"
fqdn: ""
ip: "10.165.18.3"
vlan: ""
services: ["switching", "branch-access", "management"]
owner: "Network & Security Operations Team"
related_entities: ["fw-fortigate-tulkarm-01", "rtr-tulkarm-01"]
knowledge_status: "unverified"
source: "MNE_Infrastructure/BRANCH_CONNECTIVITY_BASELINE.md"
last_verified: null
freshness_ttl_hours: 720
---

# Canonical Facts — Tulkarm Branch Access Switch

> **Entity ID:** `sw-cisco-tulkarm-01`
> **Truth Status:** Documented baseline; not live-verified in Release 2

## Management Details

- **Hostname:** `sw-access-tulkarm`
- **Management IP:** `10.165.18.3`
- **Branch subnet:** `10.165.18.0/24`
- **Branch gateway:** `10.165.18.1` (`fw-fortigate-tulkarm-01`)
- **Source basis:** Ministry branch-connectivity baseline and the Release 1 Tulkarm switch connection profile.

This record must not be promoted to `live_verified` without fresh attributable evidence for this exact switch.
