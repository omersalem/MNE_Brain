# Security Profiles (UTM) — FortiOS 7.4.11

## SSL/TLS Inspection

> Required for deep inspection of HTTPS traffic. Without it, AV/IPS/WebFilter only see encrypted headers.

### GUI: Security Profiles > SSL/SSH Inspection

```bash
# Certificate inspection (SNI-based, no decrypt)
config firewall ssl-ssh-profile
  edit "certificate-inspection"
    set comment "Inspect certificate only — no decrypt"
    config https
      set ports 443
      set status certificate-inspection
    end
  next
end

# Deep (full SSL) inspection — decrypt + re-encrypt
config firewall ssl-ssh-profile
  edit "deep-inspection"
    set comment "Full SSL decrypt and inspect"
    config https
      set ports 443
      set status deep-inspection
    end
    # CA cert used to resign inspected traffic
    set caname "Fortinet_CA_SSL"
    # Exemptions
    config ssl-exempt
      edit 1
        set address "banking-sites"    # address group
      next
    end
  next
end
```

## Antivirus (AV) Profile

### GUI: Security Profiles > AntiVirus

```bash
config antivirus profile
  edit "AV-Standard"
    set comment "Standard AV profile"
    config http
      set av-scan enable
      set outbreak-prevention enable
      set options scan
    end
    config ftp
      set av-scan enable
      set options scan
    end
    config smtp
      set av-scan enable
      set executables virus
    end
    config pop3
      set av-scan enable
    end
    config imap
      set av-scan enable
    end
    config https
      set av-scan enable
      set options scan
    end
    set scan-mode default         # or: legacy, quick
  next
end

# AV database info
# diag antivirus database-info
```

## IPS (Intrusion Prevention System)

### GUI: Security Profiles > Intrusion Prevention

```bash
config ips sensor
  edit "IPS-Standard"
    set comment "Standard IPS protection"
    config entries
      # Block all critical + high severity
      edit 1
        set rule all
        set severity critical high
        set action block
        set log enable
      next
      # Monitor medium severity
      edit 2
        set rule all
        set severity medium
        set action monitor
        set log enable
      next
    end
    # IPS signature overrides
    config override
      edit 1
        set rule-id 12345         # specific rule ID
        set action block
        set log enable
        set status enable
      next
    end
  next
end

# Restart IPS engine if needed
# diag test appl ipsmonitor 99
# diag test appl ipsmonitor 2    # enable/disable
# diag ips packet status         # IPS packet statistics
```

## Web Filter

### GUI: Security Profiles > Web Filter

```bash
config webfilter profile
  edit "WebFilter-Standard"
    config ftgd-wf
      set options error-allow    # allow on FortiGuard error
      config filters
        # Action per category (42=Pornography, 26=Gambling, etc.)
        edit 1
          set category 2         # Drug Abuse
          set action block
        next
        edit 2
          set category 42        # Pornography
          set action block
        next
        edit 3
          set category 26        # Gambling
          set action block
        next
      end
    end
    # URL filter — custom allow/block
    config url-filter
      edit 1
        set name "Block-Social"
        set type wildcard
        set url "*.facebook.com"
        set action block
      next
      edit 2
        set name "Allow-Google"
        set type wildcard
        set url "*.google.com"
        set action allow
      next
    end
    set web-content-log enable
    set log-all-url enable        # log all visited URLs
  next
end

# WebFilter diagnostics
# diag debug rating              # FortiGuard rating server info
# diag webfilter fortiguard statistics list
# diag webfilter fortiguard cache dump
# diag test appl urlfilter 1     # list test commands
```

## Application Control

### GUI: Security Profiles > Application Control

```bash
config application list
  edit "AppCtrl-Standard"
    config entries
      # Block P2P
      edit 1
        set application 33        # BitTorrent
        set action block
        set log enable
      next
      # Monitor social media
      edit 2
        set category 6            # Social Media
        set action monitor
        set log enable
      next
    end
    set unknown-application-action allow
  next
end
```

## DNS Filter

### GUI: Security Profiles > DNS Filter

```bash
config dnsfilter profile
  edit "DNS-Standard"
    set comment "Block malicious domains"
    config ftgd-dns
      config filters
        edit 1
          set category 26         # category 26 = Gambling
          set action block
        next
      end
    end
    set redirect-botnet-c-c enable  # block botnet C&C
    set log-all-domain enable
  next
end
```

## Email Filter (Anti-Spam)

```bash
config emailfilter profile
  edit "AS-Standard"
    set spam-log enable
    config imap
      set log-all enable
      set action tag              # tag spam in subject
    end
    config smtp
      set log-all enable
      set action discard
    end
  next
end
```

## File Filter

```bash
config file-filter profile
  edit "Block-Executables"
    config rules
      edit 1
        set name "Block-EXE"
        set protocol http ftp smtp imap
        set action block
        set file-type "bat" "cmd" "exe" "msi" "vbs"
      next
    end
  next
end
```

## Applying Security Profiles to Policy

```bash
# Apply all UTM profiles in a policy
config firewall policy
  edit 1
    # ... (srcintf, dstintf, etc.)
    set utm-status enable
    set av-profile "AV-Standard"
    set ips-sensor "IPS-Standard"
    set application-list "AppCtrl-Standard"
    set webfilter-profile "WebFilter-Standard"
    set dnsfilter-profile "DNS-Standard"
    set emailfilter-profile "AS-Standard"
    set ssl-ssh-profile "deep-inspection"
    set profile-protocol-options "default"
    set logtraffic all
  next
end
```

## FortiGuard Updates

```bash
diag autoupdate status             # summary of FortiGuard status
diag autoupdate versions           # detailed version of each package
exec update-now                    # manual update trigger
diag debug appl update -1          # real-time update debugging
diag test update info              # update + license info
```
