---
id: "MNE-AD-DC-01"
title: "MNE-DC1 (Primary Domain Controller)"
type: "ad_domain_controller"
status: "active"
vendor: "Microsoft"
os: "Windows Server 2022"
mgmt_ip: "172.23.71.27"
site: "HQ"
owner: "SysAdmin-Team"
criticality: "critical"
environment: "production"
last_review: "2026-07-24"
tags:
  - ministry/microsoft/active-directory
---

# MNE-DC1 (Primary Domain Controller)

Context: [[index-microsoft]] | Domain: `mne.gov.ps`

## Server Attributes
- **Server Name:** MNE-DC1
- **Management IP:** `172.23.71.27`
- **Role:** Primary Active Directory Domain Controller & AD-Integrated DNS Server

## Key Services Provided
- Kerberos & NTLM User/Computer Authentication
- Authoritative DNS for `mne.gov.ps` ([[dns-zone-mne-gov-ps]])
- Group Policy Object (GPO) Distribution

## Replicated Domain Controllers
- [[ad-dc-02]] (`MNE-DC2`: `172.23.71.28`)

## Dependent Services
- [[exch-srv-01]], [[exch-srv-02]]
- [[sccm-srv-01]]
- [[vpn-ssl-hq]]
