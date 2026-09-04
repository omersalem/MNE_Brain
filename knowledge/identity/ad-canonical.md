---
id: "dc-windows-ad-01"
name: "Primary Domain Controller (AD/DNS)"
category: "identity"
aliases: ["active directory", "ad", "dc-01", "domain-controller", "172.23.71.27"]
hostname: "dc-windows-ad-01"
fqdn: "MNE-DC1.mne.gov.ps"
ip: "172.23.71.27"
vlan: "71"
services: ["active-directory", "dns", "kerberos", "ldap"]
owner: "Identity & Security Team"
related_entities: ["fw-fortigate-hq-01", "dc-mne-ad-01"]
knowledge_status: "unverified"
source: "docs/company_docs/Ministry_Manual/MASTER_ASSET_INVENTORY.md"
last_verified: null
freshness_ttl_hours: 720
---

# Canonical Facts — Primary Domain Controller (AD/DNS)

> **Entity ID:** `dc-windows-ad-01`  
> **Trust Level:** Level 3 (Canonical Vault Fact)  
> **Truth Status:** Documented legacy record pointing to MNE-DC1 (`172.23.71.27`)

---

## 🏛️ Identity & Server Details
- **Hostname:** `MNE-DC1` (legacy reference `dc-windows-ad-01`)
- **Management IP:** `172.23.71.27` (VLAN 71)
- **OS:** Windows Server 2022 Datacenter
- **Domain:** mne.gov.ps
- **Roles:** Active Directory Domain Services, DNS Server, Global Catalog
