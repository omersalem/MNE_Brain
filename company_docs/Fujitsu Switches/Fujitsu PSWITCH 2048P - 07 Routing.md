# 07 — L3 Routing (OSPF / BGP / RIP / VRRP / Static / ECMP)
## Fujitsu PSWITCH 2048P (ET-7648BFRA-FOS) | FW 1.3.x

---

## SHOW COMMANDS

```bash
show ip route
show ip route summary
show ip interface brief
show ip interface 0/1
show arp
show arp interface 0/1
show ip ospf
show ip ospf neighbor
show ip ospf database
show ip ospf interface
show ip bgp
show ip bgp summary
show ip bgp neighbors
show ip rip
show vrrp
show vrrp interface vlan 100
show ip ecmp
show ip vrf
```

---

## ENABLING IP ROUTING

```
(Config)# ip routing                    ← enable IPv4 routing
(Config)# ipv6 unicast-routing         ← enable IPv6 routing
```

---

## ROUTED INTERFACES

### Physical Routed Port (L3)
```
(Config)# interface 0/1
(Interface 0/1)# no switchport                          ← convert to routed port
(Interface 0/1)# ip address 10.0.0.1 255.255.255.0
(Interface 0/1)# no shutdown
```

### SVI (VLAN Interface)
```
(Config)# interface vlan 100
(Interface-vlan 100)# ip address 192.168.100.1 255.255.255.0
(Interface-vlan 100)# ipv6 address 2001:db8:1::1/64
(Interface-vlan 100)# no shutdown
```

### Loopback Interface
```
(Config)# interface loopback 0
(Interface-loopback 0)# ip address 1.1.1.1 255.255.255.255
```

### Unnumbered Interface (IPv4)
```
(Interface 0/1)# ip unnumbered loopback 0
```

---

## STATIC ROUTES

```
# IPv4 static route
(Config)# ip route 10.10.0.0 255.255.0.0 192.168.1.254
(Config)# ip route 0.0.0.0 0.0.0.0 192.168.1.1            ← default route

# Two next-hops (ECMP static)
(Config)# ip route 10.10.0.0 255.255.0.0 192.168.1.254
(Config)# ip route 10.10.0.0 255.255.0.0 192.168.2.254

# IPv6 static
(Config)# ipv6 route 2001:db8::/32 2001:db8::1

show ip route static
```

---

## ARP

```
(Config)# arp 192.168.1.10 00:11:22:33:44:55 vlan 100   ← static ARP
(Config)# ip proxy-arp                                    ← Proxy ARP global
(Interface vlan 100)# ip proxy-arp                        ← per interface

clear arp-cache
show arp
```

---

## OSPF (IPv4 — v2)

```
(Config)# router ospf 1
(Config-router)# router-id 1.1.1.1
(Config-router)# network 192.168.1.0 0.0.0.255 area 0
(Config-router)# network 10.0.0.0 0.255.255.255 area 1
(Config-router)# area 1 stub                                ← stub area
(Config-router)# redistribute connected
(Config-router)# redistribute static
(Config-router)# default-information originate always
(Config-router)# passive-interface vlan 100               ← no hello on this SVI
(Config-router)# exit

# Per interface OSPF cost
(Interface vlan 100)# ip ospf cost 100
(Interface vlan 100)# ip ospf priority 10
(Interface vlan 100)# ip ospf hello-interval 5
(Interface vlan 100)# ip ospf dead-interval 20
(Interface vlan 100)# ip ospf authentication message-digest
(Interface vlan 100)# ip ospf message-digest-key 1 md5 mypassword

show ip ospf neighbor
show ip ospf interface
show ip ospf database
```

### OSPF ECMP
```
(Config)# router ospf 1
(Config-router)# maximum-paths 4                   ← max 4 ECMP paths
```

### OSPFv3 (IPv6)
```
(Config)# ipv6 router ospf 1
(Config-router)# router-id 1.1.1.1
(Interface vlan 100)# ipv6 ospf 1 area 0
show ipv6 ospf neighbor
```

---

## BGP

```
(Config)# router bgp 65001
(Config-router)# bgp router-id 1.1.1.1
(Config-router)# neighbor 10.0.0.2 remote-as 65002
(Config-router)# neighbor 10.0.0.2 description "External Peer"
(Config-router)# neighbor 10.0.0.2 timers 30 90
(Config-router)# network 192.168.0.0 mask 255.255.0.0
(Config-router)# redistribute connected
(Config-router)# redistribute static

# Graceful restart
(Config-router)# bgp graceful-restart

show ip bgp summary
show ip bgp neighbors
show ip bgp
clear ip bgp *                                   ← reset all sessions
```

> **BGP Known Issue (fixed in 1.2.21):** `advertisement-interval 5` may appear
> in running config when using template peers. It is cosmetic only.

> **BGP + VRF Known Restriction:** Do NOT use loopback for BGP peering on VRF
> instances — not all neighbors establish reliably.

---

## RIP (IPv4)

```
(Config)# router rip
(Config-router)# network 192.168.1.0
(Config-router)# version 2
(Config-router)# no auto-summary
(Config-router)# passive-interface vlan 200
(Config-router)# default-information originate
(Config-router)# redistribute connected metric 1
(Config-router)# redistribute static metric 2

(Interface vlan 100)# ip rip authentication mode md5
(Interface vlan 100)# ip rip authentication key-chain mychain

show ip rip
show ip rip database
```

### RIPng (IPv6)
```
(Config)# ipv6 router rip
(Interface vlan 100)# ipv6 rip enable
```

---

## VRRP (Virtual Router Redundancy Protocol)

```
(Config)# interface vlan 100
(Interface-vlan 100)# vrrp 1 ip 192.168.100.254       ← virtual IP
(Interface-vlan 100)# vrrp 1 priority 110              ← higher = Master (default 100)
(Interface-vlan 100)# vrrp 1 preempt                   ← preemption (default on)
(Interface-vlan 100)# vrrp 1 timers advertise 1        ← 1s hello (default 1)
(Interface-vlan 100)# vrrp 1 accept-mode               ← accept traffic to virtual IP
(Interface-vlan 100)# vrrp 1 track 1 decrement 20      ← track interface/route

show vrrp
show vrrp interface vlan 100
show vrrp detail
```

---

## ECMP (Equal Cost Multi-Path)

```
(Config)# ip ecmp                            ← enable ECMP
(Config)# ip ecmp load-balance src-dst-ip    ← hashing
# Options: src-ip | dst-ip | src-dst-ip | src-dst-mac | src-dst-mac-ip

show ip ecmp
show ip route ecmp
```

---

## VRF LITE

```
(Config)# ip vrf MGMT
(Config-vrf)# rd 65001:1
(Config-vrf)# exit

(Interface vlan 100)# ip vrf forwarding MGMT
(Interface vlan 100)# ip address 10.0.0.1 255.255.255.0

show ip vrf
show ip route vrf MGMT
```

> **VRF Warning:** Multiple VRF instances may cause instability or system restart
> in worst case (known limitation FW 1.3.x).

---

## ROUTE REDISTRIBUTION MATRIX

### IPv4 → Redistributable into:
| From \ To | Connected | Static | RIP | OSPF | BGP |
|-----------|-----------|--------|-----|------|-----|
| Connected | — | No | Yes | Yes | Yes |
| Static | No | — | Yes | Yes | Yes |
| RIP | Yes | Yes | — | Yes | Yes |
| OSPF | Yes | Yes | Yes | — | Yes |
| BGP | Yes | Yes | Yes | Yes | — |

---

## UDP RELAY / IP HELPER

```
(Config)# interface vlan 100
(Interface-vlan 100)# ip helper-address 10.0.0.50
# Default forwarded UDP ports: TFTP(69), DNS(53), DHCP(67), NTP(123),
# NetBIOS-NS(137), NetBIOS-DGM(138), TACACS(49)

show ip helper-address
```

---

## IP MTU

```
(Interface vlan 100)# ip mtu 1500
# Range: 68 – 9000 bytes
show interfaces vlan 100
```
