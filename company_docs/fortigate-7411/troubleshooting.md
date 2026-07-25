# Troubleshooting & Diagnostics — FortiOS 7.4.11

## General System Diagnostics

```bash
get system status                    # version, serial, HA mode
get system performance status        # CPU, memory, sessions
diag sys top 5 30                    # process list (refresh every 5s, show 30)
                                     # sort: P=CPU, M=Memory | Ctrl+C to stop
diag debug crashlog read             # crash history
exec tac report                      # full TAC support bundle
```

## Packet Capture (Sniffer)

### GUI: Network > Diagnostics > Packet Capture

```bash
# Basic sniff — any interface, all traffic
diag sniffer packet any '' 1 0 a

# Sniff specific interface with filter
diag sniffer packet port1 'host 8.8.8.8' 6 100 l
#                  ^intf   ^filter        ^verbose ^count ^timestamp

# Verbose levels:
# 1 = show packet headers
# 3 = show packet data in hex
# 4 = show packet with interface name
# 6 = show packet raw including ethernet header

# Filter syntax (tcpdump-like):
# 'host 10.0.0.1'                    — src or dst IP
# 'src host 10.0.0.1'                — source IP only
# 'dst port 443'                     — destination port
# 'host 10.0.0.1 and port 80'        — combined filter
# 'icmp'                             — ICMP only
# 'tcp port 80 or tcp port 443'      — HTTP or HTTPS

# Capture on multiple interfaces
diag sniffer packet "port1 port2" '' 6 0 l
```

## Flow Trace (Debug Traffic Path)

### GUI: Network > Diagnostics > Debug Flow

```bash
# Step 1 — Set filter
diag debug flow filter srcip 192.168.10.100
diag debug flow filter dstip 8.8.8.8
diag debug flow filter proto 6          # TCP
diag debug flow filter dstport 443
diag debug flow filter clear            # remove filter

# Step 2 — Enable verbose output
diag debug flow show iprope enable
diag debug flow show function-name enable

# Step 3 — Start trace (100 packets)
diag debug flow trace start 100

# Step 4 — Enable debug output
diag debug enable

# Step 5 — Generate test traffic, then stop
diag debug flow trace stop
diag debug disable
diag debug reset

# What to look for in flow trace:
# "Allowed by Policy id=X"     — traffic matched policy X
# "Denied by Policy id=0"      — no policy match (implicit deny)
# "NAT'd src to X"             — source NAT applied
# "Find out route..."          — routing lookup
# "iprope_in_check() check failed" — input policy blocked it
```

## Session Table Diagnostics

```bash
# Filter sessions
diag sys session filter srcip 192.168.10.100
diag sys session filter dstip 8.8.8.8
diag sys session filter dstport 443
diag sys session filter proto 6         # TCP

# View filtered sessions
diag sys session list

# View expected sessions (ALG half-open)
diag sys session expectation list

# Session stats
diag sys session stat

# Clear sessions
diag sys session clear                  # ALL sessions (dangerous in production!)
# Or clear only filtered:
diag sys session filter srcip 192.168.10.100
diag sys session clear
```

## Connectivity Tests

```bash
# Ping from FortiGate (source interface/IP)
exec ping-options source 192.168.10.1
exec ping 8.8.8.8

# Ping with options
exec ping-options repeat-count 10
exec ping-options size 1400
exec ping-options df-bit yes
exec ping 8.8.8.8

# Traceroute
exec traceroute-options source 192.168.10.1
exec traceroute 8.8.8.8

# Telnet test (check port reachability)
exec telnet-options source 192.168.10.1
exec telnet 10.0.0.100 80

# DNS lookup
exec nslookup name google.com
exec nslookup server 8.8.8.8
```

## Routing Diagnostics

```bash
get router info routing-table all                   # active routes
get router info routing-table details x.x.x.x       # route decision for IP
get router info routing-table database              # includes inactive routes
get router info kernel                              # hardware FIB
diag firewall proute list                           # PBR entries
get router info protocols                           # active protocols

# ARP
diag ip arp list
get system arp
exec clear system arp table

# Interface IP
diag ip address list
diag netlink interface list                         # with MTU
```

## Firewall Policy Diagnostics

```bash
# Find which policy matches specific traffic
diag firewall iprope lookup \
  <src-ip> <dst-ip> <protocol-num> <src-port> <dst-port> <ingress-intf-index>

# Example: check TCP/443 from LAN to internet via port1
diag netlink interface list | grep port1            # get interface index
diag firewall iprope lookup 192.168.10.100 8.8.8.8 6 12345 443 7
# Output shows which policy or "no match"

# FQDN cache
diag test application dnsproxy 6
diagnose firewall fqdn list-all

# VIP/IP pool status
diag firewall iplist list                           # VIP IPs
diag firewall ippool list                           # IP pool IPs
```

## VPN Diagnostics

```bash
# IPsec — Phase 1 status
diag vpn ike gateway list
get vpn ike gateway

# IPsec — Phase 2 / tunnel status
diag vpn tunnel list
get vpn ipsec tunnel details

# IKE negotiation debug (real-time)
diag vpn ike log filter rem-addr4 203.0.113.50
diag debug appl ike 63
diag debug enable
# After capture:
diag debug disable
diag debug reset

# Flush (reset) tunnels
diag vpn ike gateway flush name "VPN-Branch-01"
diag vpn tunnel flush name "VPN-Branch-01-p2"

# SSL-VPN sessions
get vpn ssl monitor
diag debug appl sslvpn -1
diag debug enable
```

## Authentication Diagnostics

```bash
# Authenticated users list
diag firewall auth list
diag firewall auth filter srcip 192.168.10.100

# Test auth server
diag test authserver radius "NPS-Server" pap user1 password123
diag test authserver ldap "AD-Server" user1 password123

# FSSO
diag debug authd fsso list
diag debug authd fsso server-status
diag debug appl authd 8256
diag debug enable

# SAML debug
diag debug appl saml -1
diag debug enable
diag sys saml metadata                # FortiGate SAML metadata (admin)

# FortiToken
diag fortitoken info
```

## Performance Diagnostics

```bash
# High CPU / memory investigation
diag sys top 5 30                     # process list
# Key processes:
# cmdbsvr  — config management
# newcli   — CLI sessions
# httpsd   — GUI/API
# miglogd  — logging
# ipsengine — IPS scanning
# wad      — proxy/SSL inspect

# Session stats
diag sys session stat

# Traffic shaper stats
diag firewall shaper traffic-shaper list
diag firewall shaper traffic-shaper stats
diag firewall shaper per-ip-shaper list

# Hardware acceleration check
diag npu np7 session-stats           # NP7 offloaded sessions (high-end models)

# Disable ASIC offload per policy (for debugging)
config firewall policy
  edit 1
    set auto-asic-offload disable
  next
end
```

## Log Diagnostics

```bash
diag log test                         # generate test log messages
exec log list                         # list log files
diag test app miglogd 6               # show log queue

# Check FortiAnalyzer connectivity
exec log fortianalyzer test-connectivity
```

## Common Issues & Quick Fixes

### Traffic not passing through policy
```bash
# 1. Check routing
get router info routing-table details <dst-ip>

# 2. Check policy match
diag firewall iprope lookup <src> <dst> 6 12345 <port> <intf-index>

# 3. Run flow trace
diag debug flow filter srcip <src-ip>
diag debug flow show iprope enable
diag debug flow show function-name enable
diag debug flow trace start 20
diag debug enable
# ... generate traffic ...
diag debug disable
```

### VPN tunnel not coming up
```bash
# 1. Check phase 1 proposal mismatch
diag debug appl ike 63
diag debug enable
# Look for: "proposals do not match"

# 2. Check PSK mismatch
# Look for: "peer id does not match"

# 3. Check routing to remote peer
exec ping <remote-peer-ip>
```

### FortiAP not connecting
```bash
# 1. Check CAPWAP connectivity from AP subnet
exec ping <fortigate-ip>

# 2. Check firewall allows CAPWAP (UDP 5246/5247)
diag sniffer packet <intf> 'udp port 5246' 6 20

# 3. Check AP discovery
diag wireless-controller wlac -c wtp-all

# 4. Restart wireless controller
exec wireless-controller restart-acd
```

### High memory usage
```bash
# Check sessions
diag sys session stat | grep "total"

# Check if IPS causing issue
diag test appl ipsmonitor 2     # toggle IPS engine
# Or temporarily disable IPS profiles on policies

# Check logging queue
diag test app miglogd 6
```
