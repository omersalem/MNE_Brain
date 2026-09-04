# Firewall Policies & NAT — FortiOS 7.4.11

## Address Objects

### GUI: Policy & Objects > Addresses

```bash
# Subnet address
config firewall address
  edit "LAN-192.168.10.0/24"
    set type ipmask
    set subnet 192.168.10.0 255.255.255.0
    set comment "Internal LAN"
  next
  edit "WebServer"
    set type ipmask
    set subnet 10.0.0.100 255.255.255.255
  next
  # FQDN address
  edit "github.com"
    set type fqdn
    set fqdn "github.com"
  next
  # IP Range
  edit "DHCP-Range"
    set type iprange
    set start-ip 192.168.10.100
    set end-ip 192.168.10.200
  next
end

# Address group
config firewall addrgrp
  edit "Internal-Servers"
    set member "WebServer" "10.0.0.0/24"
  next
end
```

## Service Objects

```bash
config firewall service custom
  edit "Custom-App-8080"
    set protocol TCP/UDP
    set tcp-portrange 8080
  next
  edit "Custom-Range"
    set tcp-portrange 8000-9000
    set udp-portrange 5000-6000
  next
end

config firewall service group
  edit "Web-Services"
    set member "HTTP" "HTTPS" "Custom-App-8080"
  next
end
```

## Schedules

```bash
config firewall schedule recurring
  edit "Business-Hours"
    set day monday tuesday wednesday thursday friday
    set start 08:00
    set end 18:00
  next
end

config firewall schedule onetime
  edit "Maintenance-Window"
    set start 00:00:2024/12/01
    set end 06:00:2024/12/01
  next
end
```

## Firewall Policies (IPv4)

### GUI: Policy & Objects > Firewall Policy

```bash
config firewall policy
  edit 1
    set name "LAN-to-WAN"
    set srcintf "port3"          # source interface (or zone)
    set dstintf "port1"          # destination interface
    set srcaddr "192.168.10.0/24"
    set dstaddr "all"
    set action accept
    set schedule "always"
    set service "ALL"
    set logtraffic all           # log all; or: utm (only UTM); or: disable
    set nat enable               # SNAT using outgoing interface IP
    # UTM profiles (optional)
    set utm-status enable
    set av-profile "default"
    set ips-sensor "default"
    set application-list "default"
    set webfilter-profile "default"
    set ssl-ssh-profile "certificate-inspection"
    set profile-protocol-options "default"
    set comments "Main LAN internet access"
  next
  edit 2
    set name "DMZ-to-LAN-DENY"
    set srcintf "port4"
    set dstintf "port3"
    set srcaddr "all"
    set dstaddr "all"
    set action deny
    set schedule "always"
    set service "ALL"
    set logtraffic all
    set comments "Block DMZ from accessing LAN"
  next
end

# Policy ordering — top-down, first match wins
# In GUI: drag to reorder; in CLI: use policy move command
config firewall policy
  move 2 after 1   # move policy 2 after policy 1
end
```

## Destination NAT — Virtual IPs (VIP)

### GUI: Policy & Objects > Virtual IPs

```bash
# DNAT — map external IP:port to internal server
config firewall vip
  edit "WebServer-VIP"
    set extintf "port1"
    set extip 203.0.113.10        # external IP on WAN
    set mappedip 10.0.0.100       # internal server IP
    set portforward enable
    set protocol tcp
    set extport 443
    set mappedport 443
    set comment "HTTPS to web server"
  next
  # Full IP mapping (no port restriction)
  edit "Server-FullNAT"
    set extintf "port1"
    set extip 203.0.113.20
    set mappedip 10.0.0.200
  next
end

# VIP Group
config firewall vipgrp
  edit "DMZ-VIPs"
    set interface "port1"
    set member "WebServer-VIP" "Server-FullNAT"
  next
end

# VIP must be used as dstaddr in a firewall policy
config firewall policy
  edit 100
    set name "VIP-WebServer"
    set srcintf "port1"           # WAN interface
    set dstintf "port4"           # DMZ interface
    set srcaddr "all"
    set dstaddr "WebServer-VIP"   # VIP object
    set action accept
    set schedule "always"
    set service "HTTPS"
    set nat disable               # NAT already done by VIP
  next
end
```

## Source NAT — IP Pools

```bash
# Overload NAT pool (PAT)
config firewall ippool
  edit "ISP2-Pool"
    set type overload
    set startip 198.51.100.10
    set endip 198.51.100.20
    set comment "NAT pool for second ISP"
  next
  # Fixed port NAT (1:1 source NAT)
  edit "Server-SNAT"
    set type fixed-port-range
    set startip 198.51.100.50
    set endip 198.51.100.50
  next
end

# Apply IP pool in policy
config firewall policy
  edit 50
    set name "SNAT-with-pool"
    set srcintf "port3"
    set dstintf "port2"
    set srcaddr "all"
    set dstaddr "all"
    set action accept
    set schedule "always"
    set service "ALL"
    set nat enable
    set ippool enable
    set poolname "ISP2-Pool"
  next
end
```

## Central SNAT & DNAT

```bash
# GUI: Policy & Objects > Central SNAT (must enable in System > Feature Visibility)
config firewall central-snat-map
  edit 1
    set srcintf "port3"
    set dstintf "port1"
    set orig-addr "all"
    set dst-addr "all"
    set nat enable
    set nat-ippool "ISP2-Pool"
    set protocol 0              # all protocols
  next
end
```

## Local-In Policy (Firewall for Traffic TO FortiGate)

```bash
config firewall local-in-policy
  edit 1
    set intf "port1"             # WAN interface
    set srcaddr "Mgmt-Hosts"     # only these IPs can access FGT mgmt
    set dstaddr "all"
    set action accept
    set service "HTTPS" "SSH"
    set schedule "always"
  next
  edit 2
    set intf "port1"
    set srcaddr "all"
    set dstaddr "all"
    set action deny
    set service "ALL"
    set schedule "always"
  next
end
```

## Firewall Authentication (Captive Portal / FSSO)

```bash
# Identity-based policy — require user authentication
config firewall policy
  edit 200
    set srcintf "port3"
    set dstintf "port1"
    set srcaddr "all"
    set dstaddr "all"
    set action accept
    set schedule "always"
    set service "ALL"
    set nat enable
    set groups "Domain-Users"    # LDAP/RADIUS group
    set logtraffic all
  next
end
```

## Firewall Policy Diagnostics

```bash
# Check which policy matches traffic
diag firewall iprope lookup <src-ip> <dst-ip> <protocol> <src-port> <dst-port> <src-intf>

# List all policies with hit counts
config firewall policy
show

# Policy hit counts in GUI: Policy & Objects > Firewall Policy (column: Bytes/Sessions)

# Session table
diag sys session filter srcip 192.168.10.100
diag sys session filter dstip 8.8.8.8
diag sys session list

# Clear sessions
diag sys session clear           # ALL sessions (dangerous!)
diag sys session filter srcip 192.168.10.100
diag sys session clear           # only filtered sessions

# FQDN cache
diag test application dnsproxy 6   # dump FQDN DNS cache
diagnose firewall fqdn list-all    # all FQDN resolutions
```
