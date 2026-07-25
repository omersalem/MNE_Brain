---
id: "MNE-TMPL-FG"
title: "FortiGate Firewall Template"
type: "fortigate_device"
status: "active"
vendor: "Fortinet"
model: "FortiGate"
firmware: "FortiOS 7.2"
site: "HQ|Branch"
owner: "SecOps-Team"
criticality: "critical"
environment: "production"
last_review: "YYYY-MM-DD"
tags:
  - ministry/security/fortigate
---

# {{title}}

Context: [[index-network-and-security]] | Site: [[site-hq]]

## Management & Reachability
- **Management IP:** 
- **HA Status:** Active-Passive / Standalone

## Interfaces & Zone Bindings
- **WAN Interface:** port1 (WAN Uplink)
- **LAN Interface:** port2 (Core Switch Trunk)
- **DMZ Interface:** port3 (F5 / WAF Zone)

## Firewall Policies & Security Objects
- **Policy 101:** Outbound Internet Access
- **Policy 104:** F5 VIP Publishing Pass-Through
- **SSL-VPN Tunnel:** [[vpn-ssl-hq]]

## Upstream & Downstream Dependencies
- **Upstream Router:** [[rtr-cisco-wan-01]]
- **Downstream Core Switch:** [[sw-cisco-core-01]]
- **Connected WAF:** [[f5-vip-public-98]]
