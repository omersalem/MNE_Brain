---
id: "MNE-SITE-BRANCH-HEBRON-GOLD"
title: "Hebron Gold Branch Office"
type: "site_branch"
status: "active"
site_code: "BR-HEBRON-GOLD"
subnet: "10.40.19.0/24"
fw_ip: "10.40.19.1"
sw_ip: "10.40.19.3"
owner: "Network-Team"
criticality: "high"
environment: "production"
last_review: "2026-07-24"
tags:
  - ministry/site/branch
---

# Hebron Gold Branch Office

Context: [[site-hq]] | Parent: [[index-network-and-security]]

## Branch Overview
- **Branch Name:** Hebron Gold Branch Office
- **Subnet Allocation:** `10.40.19.0/24`
- **HQ Gateway Interconnect:** [[fw-fortigate-hq-01]] (Port 3 Central Branch Gateway `172.23.13.201`)

## On-Site Network & Security Devices
- **Branch FortiGate Firewall:** `[[fw-fortigate-hebron-gold]]` (`10.40.19.1`)
- **Branch Switch:** `[[sw-access-hebron-gold]]` (`10.40.19.3`)

## Connection Profiles
- Firewall Connection: `[[conn-fw-fortigate-hebron-gold]]`
- Switch Connection: `[[conn-sw-access-hebron-gold]]`

## Upstream HQ Services
- Active Directory: [[ad-dc-01]]
- DNS Resolution: [[dns-zone-mne-gov-ps]]
