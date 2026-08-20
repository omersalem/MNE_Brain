---
id: "dc-windows-ad-01"
name: "Primary Domain Controller (AD/DNS)"
category: "identity"
aliases: ["active directory", "ad", "dc-01", "domain-controller", "172.23.19.20"]
hostname: "dc-windows-ad-01"
fqdn: "dc-windows-ad-01.mne.gov.ps"
ip: "172.23.19.20"
vlan: "19"
services: ["active-directory", "dns", "kerberos", "ldap"]
owner: "Identity & Security Team"
related_entities: ["fw-fortigate-hq-01"]
knowledge_status: "unverified"
source: "legacy_release_2_import"
last_verified: null
freshness_ttl_hours: 720
---

# Canonical Facts — Primary Domain Controller (AD/DNS)

> **Entity ID:** `dc-windows-ad-01`  
> **Trust Level:** Level 3 (Canonical Vault Fact)  
> **Last Verified:** 2026-07-30T10:00:00Z  

---

## 🏛️ Identity & Server Details
- **Hostname:** `dc-windows-ad-01`
- **Management IP:** `172.23.19.20`
- **OS:** Windows Server 2022 Datacenter
- **Domain:** mne.gov.ps
- **Roles:** Active Directory Domain Services, DNS Server, Global Catalog
