# 09 — Security & AAA (RADIUS / TACACS+ / LDAP / 802.1X / ACL / DAI / Source Guard)
## Fujitsu PSWITCH 2048P (ET-7648BFRA-FOS) | FW 1.3.x

---

## SHOW COMMANDS

```bash
show authentication
show dot1x
show dot1x interface 0/1
show radius servers
show tacacs
show ldap
show ip access-lists
show mac access-lists
show ip source binding
show arp inspection
show arp inspection statistics
show dos-control
```

---

## USER MANAGEMENT

```
(Config)# username admin password Admin@1234
(Config)# username oper privilege 1 password Oper@1234
# Privilege: 1 = read-only, 15 = full access
show users accounts

# Password aging
(Config)# password aging 90
(Config)# password length minimum 8
(Config)# password history 5
```

---

## RADIUS

```
(Config)# radius server host 10.0.0.100
(Config)# radius server host 10.0.0.100 auth-port 1812 acct-port 1813
(Config)# radius server host 10.0.0.100 key MySecret
(Config)# radius server host 10.0.0.100 priority 1
(Config)# radius server host 10.0.0.100 timeout 5
(Config)# radius server host 10.0.0.100 retransmit 3

show radius servers
show radius statistics
```

### RADIUS Dynamic VLAN Assignment
```
# RADIUS must return:
#   Tunnel-Type = VLAN (13)
#   Tunnel-Medium-Type = IEEE-802 (6)
#   Tunnel-Private-Group-Id = <VLAN-ID>
(Config)# aaa authorization network default radius
```

---

## TACACS+

```
(Config)# tacacs-server host 10.0.0.200
(Config)# tacacs-server host 10.0.0.200 key TacSecret
(Config)# tacacs-server host 10.0.0.200 port 49
(Config)# tacacs-server host 10.0.0.200 timeout 5

show tacacs
```

---

## LDAP

```
(Config)# ldap-server host 10.0.0.30 searchdn "dc=example,dc=com"
(Config)# ldap-server host 10.0.0.30 binddn "cn=admin,dc=example,dc=com"
(Config)# ldap-server host 10.0.0.30 password LdapSecret

# Login with OU: User:test002,ou=OrgUnit
# (required for users under an OU)

show ldap
```

> **LDAP Memory Leak (fixed in v1.2.16):** If LDAP server is unreachable,
> each failed connection leaks small memory → reboot required if repeated.
> Ensure LDAP server is always reachable.

---

## AAA AUTHENTICATION

```
(Config)# aaa authentication login default local radius
(Config)# aaa authentication login default radius local
(Config)# aaa authentication enable default radius enable
(Config)# aaa authentication dot1x default radius

# Accounting
(Config)# aaa accounting dot1x default start-stop radius
```

---

## 802.1X PORT-BASED AUTHENTICATION

```
(Config)# dot1x system-auth-control              ← enable 802.1X globally

(Interface 0/1)# dot1x port-control auto         ← enable on port
(Interface 0/1)# dot1x port-control force-authorized    ← bypass auth
(Interface 0/1)# dot1x port-control force-unauthorized  ← block all

(Interface 0/1)# dot1x timeout tx-period 30      ← EAP retransmit timer
(Interface 0/1)# dot1x timeout quiet-period 60   ← wait after failure
(Interface 0/1)# dot1x max-req 2                 ← max EAP requests
(Interface 0/1)# dot1x reauthentication          ← enable re-auth
(Interface 0/1)# dot1x timeout reauth-period 3600

show dot1x
show dot1x interface 0/1
```

### 802.1X MAC-Based Authentication
```
(Interface 0/1)# dot1x mac-auth-bypass
(Interface 0/1)# dot1x port-control auto
```

### 802.1X Supplicant Mode (switch as client)
```
(Interface 0/49)# dot1x pae supplicant
(Interface 0/49)# dot1x credentials username MySwitch password MyPass
```

---

## ACL (Access Control Lists)

### IP ACL (Extended)
```
(Config)# ip access-list extended BLOCK-FTP
(Config-ext-nacl)# deny tcp 10.0.0.0 0.0.0.255 any eq 21
(Config-ext-nacl)# permit ip any any
(Config-ext-nacl)# exit

(Interface 0/1)# ip access-group BLOCK-FTP in

show ip access-lists
show ip access-lists BLOCK-FTP
```

### IP ACL (Standard)
```
(Config)# ip access-list standard MGMT-ACL
(Config-std-nacl)# permit 10.0.0.0 0.0.0.255
(Config-std-nacl)# deny any
(Config-std-nacl)# exit
```

### MAC ACL
```
(Config)# mac access-list extended BLOCK-MAC
(Config-mac-nacl)# deny 00:11:22:33:44:55 0:0:0:0:0:0 any
(Config-mac-nacl)# permit any any
(Config-mac-nacl)# exit

(Interface 0/1)# mac access-group BLOCK-MAC in
show mac access-lists
```

---

## DYNAMIC ARP INSPECTION (DAI)

```
(Config)# ip arp inspection vlan 100
(Interface 0/49)# ip arp inspection trust         ← trust uplink
(Interface 0/1)# ip arp inspection limit rate 100

show arp inspection
show arp inspection statistics
clear arp inspection statistics
```

---

## IP SOURCE GUARD

```
(Config)# ip dhcp snooping                        ← prerequisite
(Config)# ip dhcp snooping vlan 100
(Interface 0/1)# ip verify source                 ← enable IP Source Guard
(Interface 0/1)# ip verify source port-security   ← also check MAC

show ip source binding
show ip verify source
```

### IPv6 Source Guard
```
(Interface 0/1)# ipv6 verify source
```

---

## DOS PROTECTION (DoS Control)

```
(Config)# dos-control all                         ← enable all DoS protections
(Config)# dos-control firstfrag                   ← drop first TCP frag
(Config)# dos-control tcpflag                     ← drop invalid TCP flags
(Config)# dos-control l4port                      ← drop same src/dst port
(Config)# dos-control sipequaldip                 ← drop SIP=DIP (Land attack)
(Config)# dos-control icmpv4 64                   ← max ICMPv4 size 64 bytes

show dos-control
```
