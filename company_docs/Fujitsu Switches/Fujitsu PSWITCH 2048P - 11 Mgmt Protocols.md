# 11 — SNMP / NETCONF / REST API / RMON
## Fujitsu PSWITCH 2048P (ET-7648BFRA-FOS) | FW 1.3.x

---

## SHOW COMMANDS

```bash
show snmp
show snmp community
show snmp trap
show snmp engineID
show snmp user
show snmp group
show rmon
show rmon statistics
show rmon alarm
show rmon events
show netconf
```

---

## SNMP v1/v2c

```
(Config)# snmp-server community public ro      ← read-only community
(Config)# snmp-server community private rw     ← read-write community

# Restrict community to specific host
(Config)# snmp-server community public ro 10.0.0.50

# Trap destination
(Config)# snmp-server host 10.0.0.100 traps version 2c public
(Config)# snmp-server enable traps

# Trap categories
(Config)# snmp-server enable traps linkUpDown
(Config)# snmp-server enable traps authentication
(Config)# snmp-server enable traps vlan
(Config)# snmp-server enable traps spanningtree

show snmp community
show snmp trap
```

---

## SNMP v3

```
# Create engine ID
(Config)# snmp-server engineID local 8000000903AABBCCDDEE

# Create view
(Config)# snmp-server view ALL iso included

# Create group
(Config)# snmp-server group ADMINGRP v3 priv read ALL write ALL

# Create user (SHA auth, AES encryption)
(Config)# snmp-server user snmpadmin ADMINGRP v3 auth sha MyAuthPass priv aes MyPrivPass

show snmp engineID
show snmp user
show snmp group
```

---

## RMON (Remote Monitoring)

```
(Config)# rmon enable

# Statistics (per port counters — Group 1)
(Config)# rmon statistics 1 interface 0/1 owner ADMIN

# Alarm (Group 3 — threshold alerting)
(Config)# rmon alarm 1 ifInOctets.1 30 absolute rising-threshold 1000000 1 falling-threshold 500000 2

# Events (Group 9 — trap/log on alarm)
(Config)# rmon event 1 log trap public description "High traffic event"

show rmon statistics
show rmon alarm
show rmon events
```

---

## NETCONF

Supported since FW 1.0.x. Schema version: **1.3.0**

### Access
- Port: 830 (default SSH-based NETCONF)
- Transport: SSH

### Supported Operations
| Operation | Description |
|-----------|-------------|
| `get` | Retrieve running state/config |
| `get-config` | Retrieve configuration |
| `edit-config` | Modify configuration |
| `copy-config` | Copy config datastores |
| `delete-config` | Delete a datastore |
| `lock` / `unlock` | Lock configuration |
| `close-session` | Close NETCONF session |
| `kill-session` | Terminate another session |

### Enable NETCONF
```
(Config)# netconf
show netconf
```

### IMPORTANT RESTRICTIONS
The following commands **MUST NOT** be used via NETCONF or scripting
(will cause instability or crash):
```
show, copy, clear, application, arp, bootselect, dir usb, eject usb,
erase factory-defaults, help, logout, ping, quit, reboot, reload,
renew dhcp, script, telnet, traceroute, udld reset, enable password
```

### OVSDB (Open vSwitch Database)
- Schema: OVSDB Hardware VTEP schema v1.3.0
- Transport: JSON-RPC over TCP
- **Note:** Latest OVSDB tables (`logical router`, `replication mode`) are **NOT** supported
- VXLAN-related MIB files are **NOT** supported

---

## REST API (Web GUI API — requires FW 1.3.40+)

### Enable
```
(Config)# ip http server enable
(Config)# ip https server enable
```

### Access
```
GET  https://<switch-ip>/rest/v1/...
POST https://<switch-ip>/rest/v1/...
```

### Authentication
Basic Auth using local username/password.

### Common Endpoints (Representative)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/rest/v1/system` | System info |
| GET | `/rest/v1/interface` | All interfaces |
| GET | `/rest/v1/interface/0%2F1` | Port 0/1 detail |
| GET | `/rest/v1/vlan` | All VLANs |
| POST | `/rest/v1/vlan` | Create VLAN |
| GET | `/rest/v1/bgp` | BGP config |
| GET | `/rest/v1/ospf` | OSPF config |

> Port encoding: `/` → `%2F` so `interface 0/1` → `interface/0%2F1`

---

## MIB FILES SUPPORTED

Key standard MIBs supported:
```
RFC 1213   — MIB-II (ifTable, ipTable, tcpTable)
RFC 2863   — IF-MIB (extended interface stats)
RFC 2665   — EtherLike-MIB
RFC 1493   — BRIDGE-MIB
RFC 2674   — P-BRIDGE-MIB, Q-BRIDGE-MIB
RFC 4363   — IEEE 802.1X MIB
RFC 2575   — SNMP v3 MIBs
RFC 2925   — DISMAN-PING-MIB, DISMAN-TRACEROUTE-MIB (SNMP walk issues fixed in 1.2.16)
```

> **SNMP Walk Issue (fixed in 1.2.16):** SNMP GetNext on certain OIDs
> (DISMAN-PING-MIB, OSPF-MIB, PIM-STD-MIB, RIPv2-MIB) may fail or return
> wrong values in firmware prior to 1.2.16.
