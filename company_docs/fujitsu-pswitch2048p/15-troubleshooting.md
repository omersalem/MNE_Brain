# 15 — Troubleshooting & Known Issues
## Fujitsu PSWITCH 2048P (ET-7648BFRA-FOS) | FW 1.3.x

---

## DIAGNOSTIC COMMANDS (ALWAYS START HERE)

```bash
show version                          ← confirm firmware
show system                           ← hardware health
show environment                      ← fans, PSU, temperature
show interfaces status                ← all port link states
show interfaces counters errors       ← CRC, input/output errors
show logging                          ← recent system events
show running-config                   ← current active config
show tech-support                     ← full diagnostic dump
```

---

## CONNECTIVITY TROUBLESHOOTING

### Ping & Traceroute (EXEC mode only — NOT in NETCONF/script)
```
ping 192.168.1.1
ping 192.168.1.1 count 100 size 1472
ping ipv6 2001:db8::1
traceroute 8.8.8.8
traceroute ipv6 2001:db8::1
```

### Interface Down
```
show interfaces 0/1
show interfaces 0/1 status
# Check: adminState=Up, linkStatus=Down → physical issue (cable, SFP)
# Check: adminState=Down → port was shutdown manually
(Interface 0/1)# no shutdown
```

### SFP/QSFP Issues
```
show interfaces transceiver 0/1
# Check: Tx power, Rx power, Temperature, Voltage
# Low Rx power → dirty fiber or bad SFP
# Unsupported SFP → may show "not supported" or cause errors
```

### High Error Counters (CRC / Input Errors)
```
show interfaces counters errors
clear counters 0/1
# CRC errors → bad cable, bad SFP, duplex mismatch, distance exceeded
# Fix: replace cable/SFP, check auto-negotiate settings
```

---

## VLAN TROUBLESHOOTING

```
show vlan
show vlan port 0/1
show mac-addr-table vlan 100
show interfaces switchport 0/1
# Verify: port in correct VLAN, mode (access/trunk), native VLAN
```

---

## STP TROUBLESHOOTING

```
show spanning-tree
show spanning-tree interface 0/1
show spanning-tree detail
# Look for: Port in BLK state, unexpected root bridge, TCN events
# Fix: Check priority, check portfast on edge ports, check BPDU Guard
```

---

## LAG / LACP TROUBLESHOOTING

```
show lacp summary
show lacp neighbor
show port-channel brief
# LACP not forming: check mode (active/passive), check speed match, check VLAN match
# Static LAG not forming: ensure "mode on" on both ends
```

---

## VPC TROUBLESHOOTING

```
show vpc
show vpc role
show vpc peer-keepalive
show vpc consistency-parameters
show vpc statistics
```

### VPC Common Issues
| Symptom | Cause | Fix |
|---------|-------|-----|
| VPC not forming | Keepalive unreachable | Check L3 keepalive link |
| Split-brain | Peer-link down | Restore peer-link |
| Traffic interruption ~3s | Peer-link down | Expected behavior |
| Traffic interruption ~15s | Peer-link up | Expected behavior |
| Packet loss on primary | All VPC member ports down | Restore at least one member port |

---

## ROUTING TROUBLESHOOTING

```
show ip route
show ip ospf neighbor
show ip bgp summary
show arp
show ip interface brief

# OSPF neighbor stuck in INIT/EXSTART:
# → Check MTU mismatch, check authentication, check area type match

# BGP stuck in IDLE:
# → Check neighbor IP, check AS number, check reachability

# ARP not resolving:
# → Check VLAN membership, check IP interface is up, check proxy-arp setting
clear arp-cache
```

---

## DHCP TROUBLESHOOTING

```
show ip dhcp snooping
show ip dhcp snooping binding
show ip dhcp server binding

# DHCP not working through snooping:
# → Verify uplink port is trusted: ip dhcp snooping trust
# → Verify snooping enabled on correct VLAN

# DHCP relay not forwarding:
# → Verify helper-address set on SVI
# → Verify ip routing enabled
```

---

## AUTHENTICATION / AAA TROUBLESHOOTING

```
show authentication
show dot1x interface 0/1
show radius statistics

# 802.1X port stuck unauthorized:
# → Check RADIUS server reachability (ping)
# → Check shared secret match
# → Check correct VLAN returned from RADIUS

# LDAP login fails for OU user:
# → Must specify: User:username,ou=OUname
```

---

## KNOWN ISSUES & RESTRICTIONS (FW 1.3.x)

### Active Known Issues

| # | Issue | Status | Workaround |
|---|-------|--------|------------|
| 1 | Cat6 cables — no connection to Cisco Catalyst 4900M | Active | Use Cat6A or different switch port |
| 2 | LLDP ETS incompatibility message with CFX2000 | Informational | Ignore message — not a fault |
| 3 | 40G Twinax cable not supported to CFX2000 | Active | Use fiber instead |
| 4 | VPC peer-link down → ~3s traffic interruption | By design | N/A |
| 5 | VPC peer-link up → ~15s recovery | By design | N/A |
| 6 | VPC primary all ports down → packet loss on peer-link | Active | Restore at least 1 member port |
| 7 | PFC enable causes brief link down-up | By design | Apply during maintenance window |
| 8 | VRF multiple instances may cause instability | Active | Minimize VRF usage |
| 9 | BGP peering via loopback on VRF → may not establish | Active | Use physical interface instead |
| 10 | OVSDB latest tables (logical router, replication mode) not supported | Active | Use supported schema v1.3.0 |
| 11 | VXLAN MIB not supported | Active | Use REST API for VXLAN info |

### Fixed Issues (important reference)

| # | Issue | Fixed In |
|---|-------|----------|
| F1 | NETCONF/Scripting unstable with show/copy/ping etc. | 1.2.16 |
| F2 | SNMP Walk fails on DISMAN/OSPF/PIM/RIP MIBs | 1.2.16 |
| F3 | LDAP memory leak on failed connection | 1.2.16 |
| F4 | ARP multicast loss after `clear arp-cache` | 1.2.16 |
| F5 | BGP stalepath-time=1 or 3600 → routes stay Stale | 1.2.21 |
| F6 | BGP `advertisement-interval 5` appears in config | 1.2.21 |
| F7 | `temp-config.scr` temp file not deleted after copy | 1.2.21 |
| F8 | Loop protection not working on lag interface 3/64 | 1.3.40 |
| F9 | SNTP max server name length causes reboot | 1.3.40 |
| F10 | RIP `default-information originate` not working | 1.3.40 |
| F11 | OSPF NSSA default route forwarding address 0.0.0.0 | 1.3.40 |

---

## RECOVERY PROCEDURES

### Recover from Config Loss
```
# Boot and access console
# At login prompt: admin (blank password)
copy backup-config startup-config
reload
```

### Recover from Locked Out (no access)
```
# Physical console access required
# Connect console cable: 9600-8-N-1
# Login as admin (blank password default)
# Reset to factory if needed:
erase factory-defaults
reboot
```

### CPU High / System Slow
```
show process cpu
show process memory
# Identify process consuming CPU
# If caused by routing protocol: check for route flapping
# Check for STP topology changes
show spanning-tree detail | include TCN
```
