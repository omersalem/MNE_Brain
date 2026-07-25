---
id: "MNE-SEC-BLOCKED-IPS"
title: "Blocked Threat IPs & Mitigation Index"
type: "security_reference"
status: "active"
last_updated: "2026-07-25"
tags:
  - security/blocked-ips
  - fortigate/policy-275
  - f5/address-list
---

# Blocked Threat IPs & Perimeter Block Rules

This document tracks active threat IP blocks enforced on **FortiGate (`FG-MNE`)** and **F5 BIG-IP WAF**.

## Active Blocked Threat IPs Table

| IP Address | Threat Type / Description | Date Blocked | FortiGate Object / Policy | F5 Address List |
|---|---|---|---|---|
| `188.64.206.207` | High-volume RCE (Shellshock), Directory Traversal, & SQLi scanner | 2026-07-25 | `Attacker-188.64.206.207` (Group: `BLOCKED_ATTACKER_IPS`, Policy `275`) | `Blocked_Attacker_IPs` |
| `213.209.159.175` | CERT Alert (`ticket@cert.ps`) flagged spam / privilege escalation IP | 2026-07-25 | `Attacker-213.209.159.175` (Group: `BLOCKED_ATTACKER_IPS`, Policy `275`) | `Blocked_Attacker_IPs` |

---

## FortiGate Firewall Policy Details (`FG-MNE` / `172.23.70.4`)

- **Policy ID:** `275` (`BLOCK_ATTACKER_IPS`)
- **Position:** **#1** (Top of policy table, before Policy `184`)
- **Address Group:** `BLOCKED_ATTACKER_IPS`
- **Action:** `deny` (All services, log all traffic)

---

## Related Vault Records

- [[2026-07-06-privilege-escalation-incident-mitigation]]
- [[fw-fortigate-hq-01]]
