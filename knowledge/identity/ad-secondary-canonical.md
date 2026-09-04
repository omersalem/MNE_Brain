---
id: "dc-windows-ad-02"
name: "Secondary Domain Controller (AD/DNS Replica)"
category: "identity"
aliases: ["ad-secondary", "dc-02", "dc-windows-02", "172.23.71.28"]
hostname: "dc-windows-ad-02"
fqdn: "MNE-DC2.mne.gov.ps"
ip: "172.23.71.28"
vlan: "71"
services: ["active-directory", "dns-replica", "kerberos", "ldap-replica"]
owner: "Identity & Core Windows Infrastructure Team"
related_entities: ["dc-windows-ad-01", "dc-mne-ad-02", "vc-vmware-hq-01"]
knowledge_status: "unverified"
source: "docs/company_docs/Ministry_Manual/MASTER_ASSET_INVENTORY.md"
last_verified: null
freshness_ttl_hours: 720
---

# Canonical Facts — Secondary Domain Controller (AD/DNS Replica)

> **Entity ID:** `dc-windows-ad-02`
> **Trust Level:** Level 3 (Canonical Vault Fact)
> **Truth Status:** Documented legacy record pointing to MNE-DC2 (`172.23.71.28`)

## 🔑 Identity & Directory Replica Specs
- **Hostname:** `MNE-DC2` (legacy reference `dc-windows-ad-02`)
- **Management IP:** `172.23.71.28` (VLAN 71)
- **OS:** Windows Server 2022 Datacenter
- **Domain:** `mne.gov.ps`
- **Role:** Replica Active Directory Domain Controller and Failover DNS Server
