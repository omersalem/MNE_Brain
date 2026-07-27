---
id: MNE-EXCH-SRV-02
title: EXCHANGESRV2 (Secondary Mailbox Server)
type: exchange_server
status: active
vendor: Microsoft
os: Windows Server 2022
version: Exchange Server 2019
mgmt_ip: 172.23.71.36
site: HQ
owner: SysAdmin-Team
criticality: critical
environment: production
last_review: '2026-07-24'
tags:
- ministry/microsoft/exchange
aliases:
- MNE-EXCH-SRV-02
source: Canonical Audit
trust_tier: 3
last_verified: '2026-07-27'
related_entities: []
---
# EXCHANGESRV2 (Secondary Exchange Server)

Context: [[index-microsoft]] | DAG Group: `EXCH-DAG-MNE`

## Server Baseline
- **Hostname:** EXCHANGESRV2
- **Management IP:** `172.23.71.36`
- **Role:** Secondary Mailbox & CAS Role Server

## DAG Partner
- [[exch-srv-01]] (`EXCHANGESRV1`: `172.23.71.35`)
