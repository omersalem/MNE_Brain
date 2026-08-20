---
id: "dc-windows-ad-02"
name: "Secondary Domain Controller (AD/DNS Replica)"
category: "identity"
aliases: ["ad-secondary", "dc-02", "dc-windows-02", "172.23.19.21"]
hostname: "dc-windows-ad-02"
fqdn: "dc-windows-ad-02.mne.gov.ps"
ip: "172.23.19.21"
vlan: "19"
services: ["active-directory", "dns-replica", "kerberos", "ldap-replica"]
owner: "Identity & Core Windows Infrastructure Team"
related_entities: ["dc-windows-ad-01", "vc-vmware-hq-01"]
knowledge_status: "unverified"
source: "legacy_release_2_import"
last_verified: null
freshness_ttl_hours: 720
---

# Canonical Facts — Secondary Domain Controller (AD/DNS Replica)

> **Entity ID:** `dc-windows-ad-02`
> **Trust Level:** Level 3 (Canonical Vault Fact)
> **Last Verified:** 2026-08-01T12:00:00Z

## 🔑 Identity & Directory Replica Specs
- **Hostname:** `dc-windows-ad-02`
- **Management IP:** `172.23.19.21`
- **OS:** Windows Server 2022 Datacenter
- **Domain:** `mne.gov.ps`
- **Role:** Replica Active Directory Domain Controller and Failover DNS Server
