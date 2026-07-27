---
name: fortigate-7411
description: >
  Expert-level configuration and troubleshooting guide for FortiGate firewalls running
  FortiOS 7.4.11 (build 2878, Mature). Use this skill whenever the user mentions FortiGate,
  FortiOS, FortiOS 7.4, firewall policy, NAT, IPsec VPN, SSL-VPN, SD-WAN, HA cluster,
  FortiAP, wireless controller, FortiSwitch, UTM profiles (AV/IPS/WebFilter), FSSO,
  ZTNA, BGP/OSPF on FortiGate, or any CLI/GUI task on a Fortinet firewall.
  Always consult this skill for any Fortinet/FortiGate question — even if the user
  doesn't say "FortiGate" explicitly but describes a Fortinet-like scenario.
---

# FortiGate 7.4.11 — Expert Skill

FortiOS **7.4.11 build 2878** is a **Mature** (recommended stable) release in the 7.4 train.
This skill covers GUI + CLI configuration across all major feature areas.

---

## Quick Reference — Docs & Resources

| Resource | URL |
|---|---|
| Admin Guide 7.4 | https://docs.fortinet.com/document/fortigate/7.4.11/administration-guide |
| CLI Reference 7.4 | https://docs.fortinet.com/document/fortigate/7.4.3/cli-reference |
| Release Notes 7.4.11 | https://docs.fortinet.com/document/fortigate/7.4.11/fortios-release-notes |
| Upgrade Path Tool | https://docs.fortinet.com/upgradetool/fortigate |
| Support Portal | https://support.fortinet.com |
| Knowledge Base | https://community.fortinet.com |
| FortiGuard | https://www.fortiguard.com |

---

## 7.4.11 Special Notices (Critical)

1. **RSA Key minimum 2048-bit** — Certificates with RSA < 2048 bits are no longer supported.
2. **SSL-VPN removed on G-Series Entry-Level** (50G, 70G, 90G) — migrate to IPsec Dialup VPN.
3. **Hairpin traffic requires explicit policy** — after upgrade, hairpin traffic (ingress = egress interface) needs a firewall policy.
4. **SAML certificate verification relaxed** — default now requires only ONE of (response OR assertion) to be signed; was previously both required.
5. **Security Fabric** — if enabled, ALL FortiGate devices must be upgraded to 7.4.11 together.
6. **NP7 traffic shaping changes** — QoS type CLI command changed; review shaping profiles (max 100 interfaces).
7. **Downgrade causes config loss** — downgrading from 7.4.11 results in configuration loss on all models.

---

## Architecture Overview

```
FortiGate Operational Modes:
  NAT/Route Mode  — Default; interfaces have IPs, acts as router+firewall
  Transparent Mode — Acts as bridge/switch; no routing; uses forward-domain on VLANs

Traffic Processing Order (Ingress → Egress):
  1. Ingress Interface → DoS Policy
  2. IP Routing (FIB lookup)
  3. Policy-Based Routes (PBR)
  4. Firewall Policy Match (top-down, first match wins)
  5. UTM Inspection (AV/IPS/WebFilter/AppCtrl)
  6. NAT (source or destination)
  7. Egress Interface → Traffic Shaping
```

---

## Reference Files — Load When Needed

| Topic | File | Load When |
|---|---|---|
| CLI Basics & System | `references/cli-essentials.md` | Admin, backup, firmware, debug |
| Network & Routing | `references/network-routing.md` | Interfaces, VLANs, static/BGP/OSPF |
| Firewall & NAT | `references/firewall-nat.md` | Policies, VIP, IP pools, FQDN |
| VPN (IPsec + SSL) | `references/vpn.md` | Site-to-site, remote access VPN |
| HA & SD-WAN | `references/ha-sdwan.md` | Clustering, failover, SD-WAN rules |
| Security Profiles | `references/security-profiles.md` | AV, IPS, WebFilter, AppCtrl, SSL-inspect |
| WiFi Controller | `references/wifi-controller.md` | FortiAP, SSIDs, Radio, CAPWAP |
| Troubleshooting | `references/troubleshooting.md` | Packet capture, flow trace, diag commands |

**Always read the relevant reference file before answering** — it contains exact CLI syntax and GUI paths.

---

## CLI Fundamentals (Always Available)

```bash
# Navigation
config system interface    # enter config context
  edit port1               # edit/create object
    set ip 192.168.1.1 255.255.255.0
    set allowaccess ping https ssh
  next
end

# Reading config
show system interface port1        # show saved config
get system interface port1         # show running state
show full-configuration            # all settings including defaults

# Searching
show | grep -f "string"            # filter output
show system interface | grep ip    # grep within show

# Shortcuts
?          # show available commands/options at current level
Tab        # auto-complete
Ctrl+C     # cancel / abort command
Ctrl+Z     # return to top level
end        # save and exit context
abort      # exit without saving

# Aliases
alias show = 'get'  (both work for read operations)
```

---

## Default Access Information

```
Web GUI:  https://192.168.1.99 (port1 / internal / mgmt)
CLI SSH:  ssh admin@192.168.1.99
Console:  9600 baud, 8-N-1, no flow control
Username: admin
password = secret_ref("MNE_PLATFORM_READONLY_CREDENTIAL")MNE_DEVICE_READONLY_PASSWORD") on factory default)
```
