---
id: "ex-windows-mail-01"
name: "MNE Enterprise Exchange 2019 Mail Server"
category: "compute"
aliases: ["exchange", "exchange-2019", "mail-server", "172.23.71.36", "mne-mail"]
hostname: "ex-windows-mail-01"
fqdn: "mail.mne.gov.ps"
ip: "172.23.71.36"
vlan: "71"
services: ["smtp-25", "submission-587", "imaps-993", "owa-https", "winrm-5985"]
owner: "Messaging & Collaboration Systems Team"
related_entities: ["dc-mne-ad-01", "fw-fortigate-edge-01"]
knowledge_status: "unverified"
source: "legacy_release_2_import"
last_verified: null
freshness_ttl_hours: 720
---

# Canonical Facts — MNE Enterprise Exchange 2019 Mail Server

> **Entity ID:** `ex-windows-mail-01`
> **Trust Level:** Level 3 (Canonical Vault Fact)
> **Last Verified:** 2026-08-01T12:00:00Z

## 📧 Messaging & Email Infrastructure Specs
- **Hostname:** `ex-windows-mail-01`
- **Management IP:** `172.23.71.36`
- **Product:** Microsoft Exchange Server 2019 CU13 on Windows Server 2022
- **WinRM Port:** `5985/tcp` (Username: `MNE_EXCHANGE_USERNAME`)
- **OWA Public Endpoint:** `https://mail.mne.gov.ps/owa`
