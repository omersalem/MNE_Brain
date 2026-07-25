# VPN — IPsec & SSL-VPN — FortiOS 7.4.11

> **Note (7.4.11):** SSL-VPN is removed from FortiGate G-Series Entry-Level models (50G, 70G, 90G).
> Fortinet recommends migrating to IPsec Dialup VPN for remote access.

---

## IPsec VPN — Site-to-Site

### GUI: VPN > IPsec Tunnels > Create New > Site to Site

```bash
# Phase 1 (IKE) — tunnel establishment
config vpn ipsec phase1-interface
  edit "VPN-Branch-01"
    set interface "port1"          # WAN interface
    set ike-version 2              # IKEv2 recommended
    set keylife 86400              # Phase1 lifetime (seconds)
    set peertype any
    set remote-gw 203.0.113.50    # Remote peer IP (or FQDN)
    set psksecret "MyStrongPSK!"  # Pre-shared key
    set proposal aes256-sha256    # encryption-hash
    set dhgrp 14                  # DH group 14 (2048-bit)
    set dpd on-idle               # Dead Peer Detection
    set dpd-retrycount 3
    set dpd-retryinterval 30
    set comments "Branch 01 HQ tunnel"
    # For IKEv1 aggressive mode (legacy):
    # set mode aggressive
    # set aggressive-mode enable
  next
end

# Phase 2 (IPsec) — data encryption
config vpn ipsec phase2-interface
  edit "VPN-Branch-01-p2"
    set phase1name "VPN-Branch-01"
    set proposal aes256-sha256
    set dhgrp 14
    set keylifeseconds 43200       # Phase2 lifetime
    set src-subnet 192.168.10.0 255.255.255.0  # local subnet
    set dst-subnet 192.168.20.0 255.255.255.0  # remote subnet
    set pfs enable
  next
end

# Static route for VPN traffic
config router static
  edit 100
    set dst 192.168.20.0 255.255.255.0
    set device "VPN-Branch-01"     # use tunnel name as device
    set comment "Route to branch via VPN"
  next
end

# Firewall policies for VPN
config firewall policy
  # HQ → Branch
  edit 201
    set name "HQ-to-Branch-VPN"
    set srcintf "port3"
    set dstintf "VPN-Branch-01"
    set srcaddr "192.168.10.0/24"
    set dstaddr "192.168.20.0/24"
    set action accept
    set schedule "always"
    set service "ALL"
  next
  # Branch → HQ
  edit 202
    set name "Branch-to-HQ-VPN"
    set srcintf "VPN-Branch-01"
    set dstintf "port3"
    set srcaddr "192.168.20.0/24"
    set dstaddr "192.168.10.0/24"
    set action accept
    set schedule "always"
    set service "ALL"
  next
end
```

## IPsec VPN — Remote Access (Dialup)

```bash
# Phase 1 — dialup (accepts any remote IP)
config vpn ipsec phase1-interface
  edit "RA-VPN"
    set type dynamic              # dialup mode
    set interface "port1"
    set ike-version 2
    set mode-cfg enable           # push IP/DNS to client
    set proposal aes256-sha256
    set dhgrp 14 20               # DH14 + DH20 (ECP384)
    set psksecret "VPNSecret@123"
    set xauthtype auto
    set authusrgrp "VPN-Users"    # RADIUS/LDAP group for auth
    # IP assignment pool
    set ipv4-start-ip 10.100.1.10
    set ipv4-end-ip 10.100.1.100
    set ipv4-netmask 255.255.255.0
    set dns-mode auto
    set ipv4-dns-server1 192.168.10.1
    # Split tunnel
    set ipv4-split-include "Internal-Subnets"  # address group
  next
end

config vpn ipsec phase2-interface
  edit "RA-VPN-p2"
    set phase1name "RA-VPN"
    set proposal aes256-sha256
    set dhgrp 14 20
  next
end

# Allow VPN users to reach internal network
config firewall policy
  edit 300
    set name "RA-VPN-to-Internal"
    set srcintf "RA-VPN"
    set dstintf "port3"
    set srcaddr "all"
    set dstaddr "all"
    set action accept
    set schedule "always"
    set service "ALL"
  next
end
```

## IPsec VPN Diagnostics

```bash
# Real-time IKE debugging
diag debug appl ike 63
diag debug enable
# Stop debug:
diag debug disable
diag debug reset

# Filter IKE output to specific peer
diag vpn ike log filter rem-addr4 203.0.113.50
diag vpn ike log filter rem-addr4 clear        # clear filter

# Phase 1 status
diag vpn ike gateway list
get vpn ike gateway

# Phase 2 / tunnel status
diag vpn tunnel list
get vpn ipsec tunnel details

# Delete and re-negotiate tunnels
diag vpn ike gateway flush name "VPN-Branch-01"   # delete phase1
diag vpn tunnel flush name "VPN-Branch-01-p2"     # delete phase2

# IPsec crypto stats
diag vpn ipsec status

# DPD mode options
# on-demand: send probes only when traffic goes out with no response
# on-idle:   send probes when tunnel is idle
# disable:   no DPD
```

## SSL-VPN (Web + Tunnel Mode)

> Supported on standard models. **NOT supported on G-Series Entry-Level (50G/70G/90G) in 7.4.11.**

### GUI: VPN > SSL-VPN Settings + SSL-VPN Portals

```bash
# SSL-VPN settings
config vpn ssl settings
  set status enable
  set port 10443                  # change from default 443 to avoid conflict
  set servercert "Fortinet_Factory"  # or your custom cert
  # Source interfaces
  config tunnel-ip-pools
    edit "SSLVPN_TUNNEL_ADDR1"
    next
  end
  config tunnel-ipv6-pools
  end
  set dns-server1 192.168.10.1
  set wins-server1 192.168.10.10
  config authentication-rule
    edit 1
      set groups "SSL-VPN-Users"
      set portal "full-access"   # portal name
    next
  end
end

# SSL-VPN portal
config vpn ssl web portal
  edit "full-access"
    set tunnel-mode enable
    set web-mode enable
    set ip-mode range
    set ip-pools "SSLVPN_TUNNEL_ADDR1"
    set split-tunneling enable
    set split-tunneling-routing-address "Internal-Subnets"
    set dns-server1 192.168.10.1
    # Bookmarks (web mode shortcuts)
    config bookmarks
      edit "Intranet"
        set url "http://intranet.company.local"
        set apptype http
      next
    end
  next
end

# Firewall policy for SSL-VPN
config firewall policy
  edit 400
    set name "SSL-VPN-to-Internal"
    set srcintf "ssl.root"        # SSL-VPN virtual interface
    set dstintf "port3"
    set srcaddr "all"
    set dstaddr "Internal-Servers"
    set action accept
    set schedule "always"
    set service "ALL"
    set groups "SSL-VPN-Users"
    set logtraffic all
  next
end
```

## SSL-VPN Diagnostics

```bash
# Active SSL-VPN sessions (GUI: Monitor > SSL-VPN Monitor)
get vpn ssl monitor

# Real-time SSL-VPN debugging
diag debug appl sslvpn -1
diag debug enable

# SAML metadata for SSL-VPN
diag vpn ssl saml-metadata <SAML-user>

# Check SSL-VPN daemon status
diag test appl sslvpnd 0
```

## User Authentication for VPN

```bash
# Local user
config user local
  edit "vpnuser1"
    set type password
    set passwd "User@Pass123"
    set email-to "vpnuser1@company.com"
    set two-factor fortitoken-cloud  # optional 2FA
  next
end

# User group
config user group
  edit "VPN-Users"
    set member "vpnuser1"
  next
end

# RADIUS authentication server
config user radius
  edit "NPS-Server"
    set server "10.0.0.50"
    set secret "RadiusSecret"
    set auth-type auto
  next
end

# LDAP authentication
config user ldap
  edit "AD-Server"
    set server "10.0.0.10"
    set cnid "sAMAccountName"
    set dn "dc=company,dc=local"
    set type regular
    set username "svc-fortigate@company.local"
    set password "SvcPassword"
    set group-member-check user-attr
    set group-search-base "ou=Groups,dc=company,dc=local"
    set group-object-filter "(&(objectCategory=group)(member=*))"
  next
end
```
