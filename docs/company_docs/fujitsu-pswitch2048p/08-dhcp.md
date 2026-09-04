# 08 — DHCP (Client / Server / Relay / Snooping)
## Fujitsu PSWITCH 2048P (ET-7648BFRA-FOS) | FW 1.3.x

---

## SHOW COMMANDS

```bash
show ip dhcp snooping
show ip dhcp snooping binding
show ip dhcp snooping statistics
show ip dhcp relay
show ip dhcp server
show ip dhcp server binding
show ip dhcp server statistics
```

---

## DHCP CLIENT (Management Port)

```
(Config)# serviceport protocol dhcp        ← OOB port via DHCP
show serviceport
```

### DHCP Client on SVI / Routed Port
```
(Interface vlan 100)# ip address dhcp
show dhcp lease
renew dhcp
```

---

## DHCP SERVER

```
(Config)# ip dhcp pool VLAN100
(Config-dhcp-pool)# network 192.168.100.0 255.255.255.0
(Config-dhcp-pool)# default-router 192.168.100.1
(Config-dhcp-pool)# dns-server 8.8.8.8 8.8.4.4
(Config-dhcp-pool)# lease 1 0 0                   ← 1 day, 0 hours, 0 minutes
(Config-dhcp-pool)# domain-name example.com
(Config-dhcp-pool)# exit

# Excluded addresses (don't hand out)
(Config)# ip dhcp excluded-address 192.168.100.1 192.168.100.10

# Static binding (reserve IP by MAC)
(Config)# ip dhcp pool STATIC-PC1
(Config-dhcp-pool)# host 192.168.100.50 255.255.255.0
(Config-dhcp-pool)# hardware-address 00:11:22:33:44:55
(Config-dhcp-pool)# exit

show ip dhcp server
show ip dhcp server binding
show ip dhcp server statistics
clear ip dhcp binding *
```

---

## DHCP RELAY

```
(Interface vlan 100)# ip helper-address 10.0.0.50      ← relay to DHCP server

show ip dhcp relay
show ip helper-address
```

### DHCP L2 Relay (Option 82 insertion)
```
(Config)# ip dhcp l2relay
(Interface 0/1)# ip dhcp l2relay
show ip dhcp l2relay
```

---

## DHCP SNOOPING

```
(Config)# ip dhcp snooping                             ← enable globally
(Config)# ip dhcp snooping vlan 100                    ← enable on VLAN 100
(Config)# ip dhcp snooping vlan 100,200

# Trust uplink ports (facing DHCP server/relay)
(Interface 0/49)# ip dhcp snooping trust

# Rate limiting on untrusted ports
(Interface 0/1)# ip dhcp snooping limit rate 15        ← 15 pps max

show ip dhcp snooping
show ip dhcp snooping binding
show ip dhcp snooping statistics
clear ip dhcp snooping binding *
clear ip dhcp snooping statistics
```

> **Note:** DHCP snooping binding table is used by:
> - Dynamic ARP Inspection (DAI)
> - IP Source Guard
