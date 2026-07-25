# Networking — Ubuntu Server 24.04
## Netplan, ip/ss, DNS, Routes, Bonds, VLANs

---

## CRITICAL: NETWORKING STACK IN 24.04

```
Ubuntu 24.04 Server networking stack:
  Netplan v1.0 (YAML config)
    └── systemd-networkd (backend — default for servers)
  systemd-resolved (DNS resolver — stub at 127.0.0.53)
  UFW (firewall frontend — see security.md)

Config files location: /etc/netplan/*.yaml
Apply changes: netplan apply
Test changes: netplan try (reverts after 120s if no confirmation)
```

---

## NETPLAN — CONFIGURATION

### Basic DHCP Configuration
```yaml
# /etc/netplan/00-installer-config.yaml
network:
  version: 2
  renderer: networkd        # networkd (server) or NetworkManager (desktop)
  ethernets:
    enp0s3:
      dhcp4: true
      dhcp6: false
```

### Static IP Configuration
```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    enp0s3:
      addresses:
        - 192.168.1.100/24
      routes:
        - to: default
          via: 192.168.1.1
      nameservers:
        addresses: [8.8.8.8, 8.8.4.4]
        search: [domain.local]
      dhcp4: false
      dhcp6: false
```

### Multiple Interfaces
```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    enp0s3:                   # Management interface
      addresses: [192.168.1.100/24]
      routes:
        - to: default
          via: 192.168.1.1
      nameservers:
        addresses: [8.8.8.8, 1.1.1.1]
    enp0s8:                   # Secondary interface
      addresses: [10.0.0.10/24]
      dhcp4: false
```

### VLAN Configuration
```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    enp0s3:
      dhcp4: false
  vlans:
    vlan10:
      id: 10
      link: enp0s3
      addresses: [192.168.10.100/24]
      routes:
        - to: default
          via: 192.168.10.1
    vlan20:
      id: 20
      link: enp0s3
      addresses: [192.168.20.100/24]
```

### Bond (Link Aggregation)
```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    enp0s3:
      dhcp4: false
    enp0s8:
      dhcp4: false
  bonds:
    bond0:
      interfaces: [enp0s3, enp0s8]
      addresses: [192.168.1.100/24]
      routes:
        - to: default
          via: 192.168.1.1
      parameters:
        mode: active-backup          # or: balance-rr, 802.3ad (LACP)
        primary: enp0s3
        mii-monitor-interval: 100
```

### Bridge (for VMs/Containers)
```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    enp0s3:
      dhcp4: false
  bridges:
    br0:
      interfaces: [enp0s3]
      addresses: [192.168.1.100/24]
      routes:
        - to: default
          via: 192.168.1.1
      nameservers:
        addresses: [8.8.8.8]
      parameters:
        stp: false
        forward-delay: 0
```

### Static Routes
```yaml
network:
  version: 2
  ethernets:
    enp0s3:
      addresses: [192.168.1.100/24]
      routes:
        - to: default
          via: 192.168.1.1
        - to: 10.0.0.0/8         # static route to network
          via: 192.168.1.254
        - to: 172.16.0.0/12
          via: 192.168.1.253
          metric: 100
```

---

## NETPLAN — COMMANDS

```bash
# Validate config syntax
netplan generate                    # generate backend configs (dry run)

# Apply config
sudo netplan apply                  # apply immediately

# Test config safely (reverts if no confirmation in 120s)
sudo netplan try
# Then: accept (or wait 120s for auto-revert)

# Debug
sudo netplan --debug apply          # verbose output

# Show current state (24.04 new feature)
netplan status                      # current network state
netplan status --diff               # diff between config and system state
netplan status enp0s3               # specific interface

# Show IP info
sudo netplan ip leases enp0s3       # DHCP lease info
```

---

## IP COMMANDS (iproute2)

```bash
# ── ADDRESSES ──
ip addr show                        # all interfaces + IPs
ip addr show enp0s3                 # specific interface
ip -br addr show                    # brief format
ip -4 addr show                     # IPv4 only
ip -6 addr show                     # IPv6 only

# Add/remove IP (temporary — use Netplan for permanent)
ip addr add 192.168.1.50/24 dev enp0s3
ip addr del 192.168.1.50/24 dev enp0s3

# ── LINKS (Interfaces) ──
ip link show                        # all interfaces + state
ip link show enp0s3                 # specific interface
ip -br link show                    # brief
ip link set enp0s3 up               # bring interface up
ip link set enp0s3 down             # bring interface down
ip link set enp0s3 mtu 9000         # change MTU

# ── ROUTES ──
ip route show                       # routing table
ip route show table all             # all routing tables
ip route get 8.8.8.8                # which route is used for IP
ip route add 10.0.0.0/8 via 192.168.1.254          # add static route (temp)
ip route add default via 192.168.1.1               # add default gateway
ip route del 10.0.0.0/8             # remove route

# ── ARP / NEIGHBOURS ──
ip neigh show                       # ARP cache
ip neigh flush dev enp0s3           # flush ARP for interface

# ── STATISTICS ──
ip -s link show enp0s3              # interface statistics
ip -s -s link show enp0s3          # extended stats

# ── OLD COMMANDS (deprecated but still work) ──
ifconfig                            # old: ip addr equivalent
route -n                            # old: ip route equivalent
netstat -rn                         # old: routing table
```

---

## SS (Socket Statistics) — Replaces netstat

```bash
# List listening sockets
ss -lntp                            # TCP listening + PID
ss -lnup                            # UDP listening + PID
ss -lntup                           # TCP + UDP listening

# All connections
ss -ntp                             # all TCP connections
ss -antp                            # all TCP (listening + established)
ss -anup                            # all UDP

# Filter by state
ss -ntp state established           # established only
ss -ntp state time-wait             # TIME_WAIT

# Filter by port
ss -ntp sport = :22                 # source port 22
ss -ntp dport = :80                 # dest port 80
ss src :80                          # connections FROM port 80
ss dst :443                         # connections TO port 443

# Filter by address
ss dst 192.168.1.1                  # connections to specific IP
ss src 192.168.1.100                # connections from specific IP

# Show socket memory
ss -m                               # socket memory usage

# Examples:
ss -lntp | grep :80                 # who is listening on port 80?
ss -antp | grep ESTABLISHED | wc -l # count established connections
ss -ntp | grep nginx                # connections for nginx process
```

---

## DNS — systemd-resolved

```bash
# ── STATUS & INFO ──
resolvectl status                   # full DNS config + servers
resolvectl status enp0s3            # for specific interface
systemd-resolve --status            # alternative command

# Query DNS
resolvectl query google.com         # resolve hostname
resolvectl query -t MX domain.com   # MX record
resolvectl query -t NS domain.com   # NS record
resolvectl query -t SRV _ldap._tcp.domain.com  # SRV record
resolvectl query 8.8.8.8            # reverse lookup

# DNS statistics
resolvectl statistics               # cache hits, queries
resolvectl reset-statistics         # reset counters

# Flush DNS cache
resolvectl flush-caches             # flush all caches

# DNS servers
resolvectl dns                      # show configured DNS servers per interface
resolvectl dns enp0s3 8.8.8.8 1.1.1.1  # set DNS for interface (temp)

# ── CONFIGURATION ──
# /etc/systemd/resolved.conf
[Resolve]
DNS=8.8.8.8 8.8.4.4
FallbackDNS=1.1.1.1 9.9.9.9
Domains=~.
DNSSEC=no                           # or: yes, allow-downgrade
DNSOverTLS=no                       # or: yes, opportunistic
Cache=yes
DNSStubListener=yes                 # stub at 127.0.0.53

# Apply: sudo systemctl restart systemd-resolved

# ── STUB RESOLVER ──
# /etc/resolv.conf → symlink to:
# /run/systemd/resolve/stub-resolv.conf  (uses 127.0.0.53)
# or:
# /run/systemd/resolve/resolv.conf       (uses real DNS IPs)
ls -la /etc/resolv.conf             # check what it links to
cat /run/systemd/resolve/resolv.conf

# ── CLASSIC nslookup/dig ──
nslookup google.com                 # basic lookup
nslookup google.com 8.8.8.8        # use specific server
dig google.com                      # detailed lookup
dig google.com MX                   # MX records
dig @8.8.8.8 google.com            # use specific DNS server
dig +short google.com               # short output (IP only)
dig -x 8.8.8.8                      # reverse lookup
host google.com                     # simple lookup
```

---

## NETWORKCTL (systemd-networkd control)

```bash
networkctl                          # list all links/status
networkctl status                   # all interfaces detailed
networkctl status enp0s3            # specific interface
networkctl lldp                     # LLDP neighbors
networkctl reload                   # reload networkd config
networkctl reconfigure enp0s3       # reconfigure specific link

# Network link states:
# carrier  — physical link present
# routable — has IP and route
# degraded — link up but not fully configured
# off      — interface down
```

---

## CONNECTIVITY TESTING

```bash
# Basic connectivity
ping -c 4 8.8.8.8                   # ping (4 packets)
ping -c 4 -I enp0s3 8.8.8.8        # ping via specific interface
ping6 ::1                           # IPv6 ping

# Traceroute
traceroute 8.8.8.8                  # trace route (UDP)
traceroute -T 8.8.8.8               # TCP traceroute (avoids ICMP blocks)
tracepath 8.8.8.8                   # traceroute + MTU discovery
mtr 8.8.8.8                         # continuous traceroute (install: apt install mtr)

# Port testing
nc -zv 192.168.1.1 22               # test TCP port (netcat)
nc -zvu 192.168.1.1 53              # test UDP port
telnet 192.168.1.1 22               # test TCP (old method)
curl -v telnet://192.168.1.1:22     # test with curl

# HTTP/HTTPS
curl -I https://google.com          # HTTP headers
curl -v https://google.com          # verbose + headers
wget --spider https://google.com    # test URL

# Bandwidth test
iperf3 -s                           # server mode (listen)
iperf3 -c 192.168.1.1              # client mode (test to server)
iperf3 -c 192.168.1.1 -t 30       # 30 second test

# Packet capture
tcpdump -i enp0s3                   # capture all traffic
tcpdump -i enp0s3 port 80          # filter by port
tcpdump -i enp0s3 host 8.8.8.8    # filter by host
tcpdump -i enp0s3 -w /tmp/capture.pcap  # save to file
tcpdump -r /tmp/capture.pcap        # read from file
```
