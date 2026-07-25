---
id: "MNE-SITE-BRANCH-RAMALLAH-GOLD"
title: "Ramallah Gold Branch Office"
type: "site_branch"
status: "active"
site_code: "BR-RAMALLAH-GOLD"
subnet: "10.110.19.0/24"
fw_ip: "10.110.19.1"
sw_ip: "10.110.19.3"
owner: "Network-Team"
criticality: "high"
environment: "production"
last_review: "2026-07-24"
tags:
  - ministry/site/branch
---

# Ramallah Gold Branch Office

Context: [[site-hq]] | Parent: [[index-network-and-security]]

## Branch Overview
- **Branch Name:** Ramallah Gold Branch Office
- **Subnet Allocation:** `10.110.19.0/24`
- **HQ Gateway Interconnect:** [[fw-fortigate-hq-01]] (Port 3 Central Branch Gateway `172.23.13.201`)

## On-Site Network & Security Devices
- **Branch FortiGate Firewall:** `[[fw-fortigate-ramallah-gold]]` (`10.110.19.1`)
- **Branch Switch:** `[[sw-access-ramallah-gold]]` (`10.110.19.3`)

## Connection Profiles
- Firewall Connection: `[[conn-fw-fortigate-ramallah-gold]]`
- Switch Connection: `[[conn-sw-access-ramallah-gold]]`

## Upstream HQ Services
- Active Directory: [[ad-dc-01]]
- DNS Resolution: [[dns-zone-mne-gov-ps]]
