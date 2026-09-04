---
name: fujitsu-pswitch2048p
description: >
  Expert-level CLI and GUI reference for the Fujitsu PSWITCH 2048P (model ET-7648BFRA-FOS)
  running firmware 1.3.x (including 1.3.68). ALWAYS use this skill for any question about
  the Fujitsu PSWITCH 2048P, PSWITCH 2048T, or ET-7648BFRA-FOS switch — including CLI
  commands (show, configure, debug), Web GUI navigation, firmware upgrade, backup/restore,
  VLAN, LAG/LACP, VPC, STP, LLDP, SNMP, QoS, DCB, routing (OSPF/BGP/RIP/VRRP), DHCP,
  ACL, sFlow, NETCONF, REST API, EHM (End Host Mode), troubleshooting, and known issues.
  Use this skill even if the user only mentions "the switch", "the Fujitsu switch",
  "PSWITCH", or describes a Fujitsu ToR switch scenario.
---

# Fujitsu PSWITCH 2048P — Expert Reference
## Model: ET-7648BFRA-FOS | Firmware: 1.3.x (includes 1.3.68)

---

## HARDWARE OVERVIEW

| Item | Detail |
|------|--------|
| Form factor | 1U ToR Switch |
| Down-link ports | 48 × 10GbE SFP+ (0/1 – 0/48) |
| Up-link ports | 6 × 40GbE QSFP+ (0/49 – 0/54) |
| Management port | 1 × OOB RJ45 (10/100/1000) |
| Console port | 1 × EIA-232 (RJ45), 9600-8-N-1 |
| PSU | 2 × redundant (hot-swap) |
| FAN | Hot-swap fan units |
| Switch capacity | ~1.36 Tbps |

---

## CLI BASICS

### Prompt Conventions
```
(ET-7648BFRA-FOS)>          ← User EXEC mode (read-only)
(ET-7648BFRA-FOS)#          ← Privileged EXEC mode
(ET-7648BFRA-FOS)(Config)#  ← Global Config mode
(ET-7648BFRA-FOS)(Interface 0/X)#   ← Interface config
(ET-7648BFRA-FOS)(Interface lag X)# ← LAG interface config
(ET-7648BFRA-FOS)(Vlan)#    ← VLAN database mode
(ET-7648BFRA-FOS)(Router)#  ← Routing protocol config
```

### Mode Navigation
```
(ET-7648BFRA-FOS)> enable                  ← Enter privileged mode
(ET-7648BFRA-FOS)# configure               ← Enter global config
(ET-7648BFRA-FOS)(Config)# exit            ← Back one level
(ET-7648BFRA-FOS)(Config)# end             ← Back to privileged mode
(ET-7648BFRA-FOS)# disable                 ← Back to user mode
```

### CLI Shortcuts
- `Tab` — auto-complete command
- `?` — list available commands / options
- Commands can be abbreviated (e.g., `sh ver` = `show version`)
- `do <command>` — run EXEC command from config mode

---

## SECTION INDEX — REFERENCE FILES

For detailed commands, read the appropriate reference file:

| Topic | File |
|-------|------|
| System & Management | `references/01-system.md` |
| Interfaces & Ports | `references/02-interfaces.md` |
| VLAN Configuration | `references/03-vlan.md` |
| LAG / LACP / VPC | `references/04-lag-vpc.md` |
| STP / RSTP / MSTP | `references/05-stp.md` |
| LLDP / CDP / Port Mirror | `references/06-lldp-mirror.md` |
| L3 Routing (OSPF/BGP/RIP/VRRP) | `references/07-routing.md` |
| DHCP (Client/Server/Relay) | `references/08-dhcp.md` |
| Security & AAA (RADIUS/TACACS/802.1X/ACL) | `references/09-security.md` |
| QoS & DCB (PFC/ETS/ECN) | `references/10-qos-dcb.md` |
| SNMP / sFlow / NETCONF / REST API | `references/11-mgmt-protocols.md` |
| EHM (End Host Mode) | `references/12-ehm.md` |
| Firmware Upgrade & Backup/Restore | `references/13-firmware-backup.md` |
| Web GUI Navigation | `references/14-webgui.md` |
| Troubleshooting & Known Issues | `references/15-troubleshooting.md` |

---

## QUICK REFERENCE — MOST COMMON COMMANDS

### System Status
```
show version
show system
show running-config
show startup-config
show logging
show clock
show users
show sessions
show tech-support
```

### Interface Status
```
show interfaces
show interfaces 0/1
show interfaces status
show interfaces counters
show interfaces transceiver
```

### VLAN
```
show vlan
show vlan brief
show vlan id 100
```

### Layer 2
```
show mac-addr-table
show spanning-tree
show lacp summary
show port-channel brief
show lldp neighbors
```

### Layer 3
```
show ip route
show ip interface brief
show ip ospf neighbor
show ip bgp summary
show arp
```

### Save Config
```
(ET-7648BFRA-FOS)# copy running-config startup-config
```

---

## FIRMWARE 1.3.x KEY NOTES

- **1.3.40+**: REST API (Web GUI) added
- **1.3.68**: Stable mature release; all features below fully supported
- **Triple config files**: startup-config, running-config, backup-config
- **Port numbering**: Always `0/<port>` format (e.g., `0/1`, `0/49`)
- **LAG numbering**: `lag 1` through `lag 64` (max 64 LAGs, 8 members each)
- **VPC peer-link**: link-down/up causes ~3s (down) / ~15s (up) interruption — known behavior
- **OVSDB schema**: v1.3.0 (no 'logical router' or 'replication mode' table)
- **Forbidden commands in NETCONF/Scripting**: `show`, `copy`, `clear`, `ping`, `traceroute`, `reboot`, `reload` — use CLI only

---

## MANAGEMENT ACCESS

### Console
- Baud: 9600, Data: 8, Parity: None, Stop: 1, Flow: None
- Default login: `admin` / (no password)

### SSH / Telnet
```
(Config)# ip ssh server enable
(Config)# ip telnet server enable
(Config)# serviceport protocol dhcp        ← OOB port via DHCP
(Config)# serviceport ip 192.168.1.2 255.255.255.0  ← OOB static IP
```

### Default Credentials
- Username: `admin`
- password = secret_ref("MNE_PLATFORM_READONLY_CREDENTIAL")MNE_DEVICE_READONLY_PASSWORD") by default)
- Web GUI: `http://<management-IP>` or `https://<management-IP>`

---

> **INSTRUCTIONS FOR AI USING THIS SKILL:**
> Read the specific reference file matching the user's topic BEFORE answering.
> Always use `(ET-7648BFRA-FOS)` prompt format in examples.
> Port format is always `0/<N>` (e.g., `0/1`, not `gi1/0/1`).
> Confirm firmware 1.3.x context applies; note if feature requires specific sub-version.
