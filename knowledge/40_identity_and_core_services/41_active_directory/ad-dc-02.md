---
id: MNE-AD-DC-02
title: MNE-DC2 (Secondary Domain Controller)
type: ad_domain_controller
status: active
vendor: Microsoft
os: Windows Server 2022
mgmt_ip: 172.23.71.28
site: HQ
owner: SysAdmin-Team
criticality: critical
environment: production
last_review: '2026-07-24'
tags:
- ministry/microsoft/active-directory
aliases:
- MNE-AD-DC-02
source: Canonical Audit
trust_tier: 3
last_verified: '2026-07-27'
related_entities: []
---
# MNE-DC2 (Secondary Domain Controller)

Context: [[index-microsoft]] | Domain: `mne.gov.ps`

## Server Attributes
- **Server Name:** MNE-DC2
- **Management IP:** `172.23.71.28`
- **Role:** Secondary Domain Controller & AD-Integrated DNS Server

## Replication Partner
- [[ad-dc-01]] (`MNE-DC1`: `172.23.71.27`)
