---
id: "MNE-SITE-BRANCH-TUBAS"
title: "Tubas Branch Office"
type: "site_branch"
status: "active"
site_code: "BR-TUBAS"
subnet: "10.230.18.0/24"
fw_ip: "10.230.18.1"
sw_ip: "10.230.18.3"
owner: "Network-Team"
criticality: "high"
environment: "production"
last_review: "2026-07-24"
tags:
  - ministry/site/branch
---

# Tubas Branch Office

Context: [[site-hq]] | Parent: [[index-network-and-security]]

## Branch Overview
- **Branch Name:** Tubas Branch Office
- **Subnet Allocation:** `10.230.18.0/24`
- **HQ Gateway Interconnect:** [[fw-fortigate-hq-01]] (Port 3 Central Branch Gateway `172.23.13.201`)

## On-Site Network & Security Devices
- **Branch FortiGate Firewall:** `[[fw-fortigate-tubas]]` (`10.230.18.1`)
- **Branch Switch:** `[[sw-access-tubas]]` (`10.230.18.3`)

## Connection Profiles
- Firewall Connection: `[[conn-fw-fortigate-tubas]]`
- Switch Connection: `[[conn-sw-access-tubas]]`

## Upstream HQ Services
- Active Directory: [[ad-dc-01]]
- DNS Resolution: [[dns-zone-mne-gov-ps]]
