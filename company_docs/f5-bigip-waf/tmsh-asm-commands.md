# Extended TMSH ASM Command Reference — BIG-IP 17.5.1.3

## Policy Operations

```bash
# Full list of all policies with details
tmsh list asm policy all-properties

# Diff two policies
tmsh show asm policy <policy-name> diff <other-policy-name>

# Clone a policy
tmsh copy asm policy <source-policy> <destination-policy>

# Set policy enforcement mode
tmsh modify asm policy <policy-name> enforcement-mode blocking
tmsh modify asm policy <policy-name> enforcement-mode transparent

# Enable/disable signature staging globally
tmsh modify asm policy <policy-name> signature-staging true
tmsh modify asm policy <policy-name> signature-staging false
```

## URL Management

```bash
# List allowed URLs
tmsh list asm policy <policy-name> urls

# Add an explicit allowed URL
tmsh modify asm policy <policy-name> urls add { /login { type explicit protocol http } }

# Add a wildcard URL
tmsh modify asm policy <policy-name> urls add { "/*" { type wildcard } }

# Add a URL with method restrictions
tmsh modify asm policy <policy-name> urls add { /api/data { type explicit allowed-methods { GET POST } } }
```

## Parameter Management

```bash
# List parameters
tmsh list asm policy <policy-name> parameters

# Add a global parameter
tmsh modify asm policy <policy-name> parameters add { username { type explicit data-type alpha-numeric } }

# Add a sensitive parameter (masked in logs)
tmsh modify asm policy <policy-name> parameters add { password { type explicit sensitive true } }
```

## File Type Management

```bash
# List allowed file types
tmsh list asm policy <policy-name> filetypes

# Add a file type
tmsh modify asm policy <policy-name> filetypes add { php { type explicit } }

# Add wildcard file type (allow all)
tmsh modify asm policy <policy-name> filetypes add { "*" { type wildcard } }
```

## Cookie Management

```bash
# List cookies
tmsh list asm policy <policy-name> cookies

# Add an explicit cookie
tmsh modify asm policy <policy-name> cookies add { sessionid { type explicit } }

# Add a wildcard cookie (e.g., TS* for BIG-IP cookies)
tmsh modify asm policy <policy-name> cookies add { "TS*" { type wildcard } }

# Enable cookie enforcement
tmsh modify asm policy <policy-name> cookie-settings { maximumCookieHeaderLength any }
```

## Blocking Settings

```bash
# View all blocking settings
tmsh list asm policy <policy-name> blocking-settings

# Modify specific violation setting (learn alarm block)
tmsh modify asm policy <policy-name> blocking-settings { "HTTP protocol compliance failed" { alarm true block true learn true } }

# Show violations
tmsh show asm policy <policy-name> violations
```

## Signature Management

```bash
# Show all signature sets
tmsh list asm signature-set

# Show which signature sets are in a policy
tmsh list asm policy <policy-name> signature-sets

# Add a signature set to a policy
tmsh modify asm policy <policy-name> signature-sets add { "SQL Injection Signatures" { block true alarm true learn true } }

# Remove a signature set
tmsh modify asm policy <policy-name> signature-sets delete { "Generic Detection Signatures" }

# Show a specific signature
tmsh show asm attack-signature <signature-id>

# Disable a specific signature in a policy (per-policy override)
tmsh modify asm policy <policy-name> attack-signatures <signature-id> { enabled false }

# Enable staging for a specific signature
tmsh modify asm policy <policy-name> attack-signatures <signature-id> { staging true }

# Update signatures
tmsh run asm signature-update

# Show signature update status
tmsh show asm signature-file-update
```

## Bot Defense

```bash
# List bot defense profiles
tmsh list asm bot-defense profile

# Create bot defense profile
tmsh create asm bot-defense profile <name> mode alarm

# Modes: alarm | block | transparent | disabled
tmsh modify asm bot-defense profile <name> mode blocking

# Show bot defense stats
tmsh show asm bot-defense profile <name> stats

# View bot request log
tmsh show asm bot-defense requests
```

## DoS Protection

```bash
# List DoS profiles
tmsh list asm dos-protection profile

# Create a DoS profile (application-level)
tmsh create asm dos-protection profile <name> application { enabled true }

# Show DoS statistics
tmsh show asm dos-protection

# Show current DoS attacks in progress
tmsh show asm dos-attack
```

## Login Pages & Brute Force

```bash
# List login pages
tmsh list asm policy <policy-name> login-pages

# Add a login page
tmsh modify asm policy <policy-name> login-pages add {
  /login {
    access-validation {
      parameter-name username
    }
    authentication-type form
  }
}

# View brute force protection settings
tmsh list asm policy <policy-name> brute-force-attack-prevention

# Enable brute force protection
tmsh modify asm policy <policy-name> brute-force-attack-prevention { enabled true }
```

## IP Intelligence

```bash
# Show IP rep DB status
tmsh show sys iprep-status

# Show IP intelligence policy
tmsh list net ip-intelligence policy

# Check a specific IP's reputation
tmsh show sys iprep-db address <ip-address>
```

## Geolocation

```bash
# List disallowed geolocations in policy
tmsh list asm policy <policy-name> geolocation-enforcement

# Add a disallowed geolocation
tmsh modify asm policy <policy-name> geolocation-enforcement { disallowed-countries add { KP IR } }
```

## Request/Response Inspection

```bash
# View response codes allowed/disallowed
tmsh list asm policy <policy-name> response-pages

# Add an allowed HTTP response code
tmsh modify asm policy <policy-name> response-pages modify { default { response-action default } }
```

## CORS (Cross-Origin Resource Sharing)

```bash
# View CORS settings
tmsh list asm policy <policy-name> | grep -i cors

# Enable CORS in a policy
tmsh modify asm policy <policy-name> cross-origin-requests-enforcement enabled
```

## JSON / XML / GraphQL Profiles

```bash
# List JSON profiles in policy
tmsh list asm policy <policy-name> json-profiles

# Add a JSON profile to a URL
tmsh modify asm policy <policy-name> urls modify {
  /api/data {
    json-profile-reference { link https://localhost/mgmt/tm/asm/policies/<id>/json-profiles/<id> }
  }
}

# List GraphQL profiles
tmsh list asm policy <policy-name> graphql-profiles
```

## HA and Sync

```bash
# Show device group sync status
tmsh show cm sync-status

# Show all device groups
tmsh show cm device-group

# Show datasync-global-dg (CRITICAL — do not delete)
tmsh list cm device-group datasync-global-dg

# Manually sync to device group
tmsh run cm config-sync to-group <device-group-name>

# Check failover state
tmsh show sys failover
tmsh show cm failover-status
```

## Saving and Loading Configuration

```bash
# Save running config
tmsh save sys config

# Load config from a UCS archive
tmsh load sys ucs /var/local/ucs/backup.ucs

# Create UCS backup
tmsh save sys ucs /var/local/ucs/backup_$(date +%Y%m%d).ucs

# Load SCF (single config file)
tmsh load sys config file /var/tmp/bigip.conf

# View current config file
cat /config/bigip.conf | less
```

## Useful Bash Troubleshooting

```bash
# Check memory usage
free -m

# Check disk usage
df -h

# Check top processes
top

# Check TCP connections
netstat -an | grep ESTABLISHED | wc -l

# Check NTP sync
ntpq -np

# Check routing table
netstat -nr

# Check interface status
ip link show

# Check DNS resolution
dig @<dns-server> <hostname>

# Test connection to signature server
curl -v https://signatures.f5.com

# ASM database check
ls -la /var/sam/usr/share/asm/

# View ASM log in real time
tail -f /var/log/asm

# Search ASM log for specific string
grep -i "sql injection" /var/log/asm | tail -100
grep -i "blocked" /var/log/asm | tail -100
grep "<support-id>" /var/log/asm
```
