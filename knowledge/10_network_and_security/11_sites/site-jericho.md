---
id: MNE-SITE-BRANCH-JERICHO
title: Jericho Branch Office
type: site_branch
status: active
site_code: BR-JERICHO
subnet: 10.211.18.0/24
fw_ip: 10.211.18.1
sw_ip: 10.211.18.3
owner: Network-Team
criticality: high
environment: production
last_review: '2026-07-24'
tags:
- ministry/site/branch
aliases:
- MNE-SITE-BRANCH-JERICHO
source: Canonical Audit
trust_tier: 3
last_verified: '2026-07-27'
related_entities: []
---
# Jericho Branch Office

Context: [[site-hq]] | Parent: [[index-network-and-security]]

## Branch Overview
- **Branch Name:** Jericho Branch Office
- **Subnet Allocation:** `10.211.18.0/24`
- **HQ Gateway Interconnect:** [[fw-fortigate-hq-01]] (Port 3 Central Branch Gateway `172.23.13.201`)

## On-Site Network & Security Devices
- **Branch FortiGate Firewall:** `[[fw-fortigate-jericho]]` (`10.211.18.1`)
- **Branch Switch:** `[[sw-access-jericho]]` (`10.211.18.3`)

## Connection Profiles
- Firewall Connection: `[[conn-fw-fortigate-jericho]]`
- Switch Connection: `[[conn-sw-access-jericho]]`

## Upstream HQ Services
- Active Directory: [[ad-dc-01]]
- DNS Resolution: [[dns-zone-mne-gov-ps]]
