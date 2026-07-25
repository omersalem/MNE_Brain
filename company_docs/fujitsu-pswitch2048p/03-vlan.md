# 03 — VLAN Configuration
## Fujitsu PSWITCH 2048P (ET-7648BFRA-FOS) | FW 1.3.x

---

## SHOW COMMANDS

```bash
show vlan
show vlan brief
show vlan id 100
show vlan port 0/1
show vlan association subnet
show mac-addr-table
show mac-addr-table vlan 100
show mac-addr-table interface 0/5
```

---

## CREATE / DELETE VLANs

```
# Enter VLAN database mode
(ET-7648BFRA-FOS)# vlan database
(ET-7648BFRA-FOS)(Vlan)# vlan 100
(ET-7648BFRA-FOS)(Vlan)# vlan 100 name "Production"
(ET-7648BFRA-FOS)(Vlan)# vlan 100-200          ← range
(ET-7648BFRA-FOS)(Vlan)# no vlan 100            ← delete
(ET-7648BFRA-FOS)(Vlan)# exit
```

---

## UNTAGGED VLAN (ACCESS) — Example
```
# Goal: Port 0/5 → VLAN 100 (untagged/access)
(Config)# vlan database
(Vlan)# vlan 100 name "USERS"
(Vlan)# exit

(Config)# interface 0/5
(Interface 0/5)# switchport mode access
(Interface 0/5)# switchport access vlan 100
(Interface 0/5)# exit
```

---

## TAGGED VLAN (TRUNK) — Example
```
# Goal: Port 0/49 (uplink) → carry VLANs 10, 20, 30; native VLAN 1
(Config)# interface 0/49
(Interface 0/49)# switchport mode trunk
(Interface 0/49)# switchport trunk allowed vlan 10,20,30
(Interface 0/49)# switchport trunk native vlan 1
(Interface 0/49)# exit
```

---

## GENERAL MODE (Flexible Access+Trunk)
```
(Interface 0/3)# switchport mode general
(Interface 0/3)# switchport general allowed vlan add 100 tagged
(Interface 0/3)# switchport general allowed vlan add 200 untagged
(Interface 0/3)# switchport general pvid 200          ← native VLAN
```

---

## VLAN TYPES SUPPORTED

| Type | Command Keyword |
|------|----------------|
| Port-based VLAN | `switchport` |
| MAC-based VLAN | `mac-based vlan` |
| Protocol-based VLAN | `protocol-based vlan` |
| IP Subnet-based VLAN | `ip-subnet-based vlan` |
| Private VLAN (PVLAN) | `private-vlan` |
| Double VLAN (Q-in-Q) | `switchport mode dot1q-tunnel` |

### Private VLAN (PVLAN)
```
(Vlan)# vlan 100 private-vlan primary
(Vlan)# vlan 101 private-vlan community
(Vlan)# private-vlan association 100 add 101
(Interface 0/1)# switchport mode private-vlan host
(Interface 0/1)# switchport private-vlan host-association 100 101
(Interface 0/2)# switchport mode private-vlan promiscuous
(Interface 0/2)# switchport private-vlan mapping 100 add 101
show vlan private-vlan
```

### Double VLAN (Q-in-Q)
```
(Interface 0/1)# switchport mode dot1q-tunnel
(Interface 0/1)# switchport access vlan 200    ← outer VLAN
show vlan dot1q-tunnel
```

---

## GVRP (Dynamic VLAN Registration)
```
(Config)# gvrp
(Interface 0/1)# gvrp
show gvrp configuration
show gvrp statistics
```

---

## PROTECTED PORTS (Port Isolation within VLAN)
```
(Interface 0/1)# switchport protected         ← ports cannot talk to each other
show interfaces switchport
```

---

## SVI (Routed VLAN Interface — Layer 3)
```
(Config)# interface vlan 100
(Interface-vlan 100)# ip address 192.168.100.1 255.255.255.0
(Interface-vlan 100)# no shutdown
(Interface-vlan 100)# exit
show ip interface brief
show interfaces vlan 100
```

---

## MAC ADDRESS TABLE

```
# Add static MAC entry
(Config)# mac-addr-table static 00:11:22:33:44:55 vlan 100 interface 0/5

# Set aging time
(Config)# mac-addr-table aging-time 300

# Clear dynamic entries
clear mac-addr-table dynamic
clear mac-addr-table dynamic vlan 100

show mac-addr-table
show mac-addr-table count
show mac-addr-table static
```
