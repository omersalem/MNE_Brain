---
id: MNE-EXCH-SRV-01
title: EXCHANGESRV1 (Primary Mailbox Server)
type: exchange_server
status: active
vendor: Microsoft
os: Windows Server 2022
version: Exchange Server 2019
mgmt_ip: 172.23.71.35
site: HQ
owner: SysAdmin-Team
criticality: critical
environment: production
last_review: '2026-07-24'
tags:
- ministry/microsoft/exchange
aliases:
- MNE-EXCH-SRV-01
source: Canonical Audit
trust_tier: 3
last_verified: '2026-07-27'
related_entities: []
---
# EXCHANGESRV1 (Primary Exchange Server)

Context: [[index-microsoft]] | DAG Group: `EXCH-DAG-MNE`

## Server Baseline
- **Hostname:** EXCHANGESRV1
- **Management IP:** `172.23.71.35`
- **Role:** Primary Mailbox & CAS Role Server

## High Availability & DAG
- **DAG Partner:** [[exch-srv-02]] (`EXCHANGESRV2`: `172.23.71.36`)

## Infrastructure Dependencies
- Active Directory: [[ad-dc-01]], [[ad-dc-02]]
- DNS: [[dns-zone-mne-gov-ps]]
- Published WAF: [[f5-vip-public-98]]
- Hypervisor Host: [[esxi-host-01]]
- Storage: Fujitsu SAN ETERNUS [[san-fujitsu-eternus-01]]
