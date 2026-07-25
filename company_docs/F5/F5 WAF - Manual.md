---
name: f5-bigip-waf
description: >
  Expert-level guide for F5 BIG-IP Advanced WAF (ASM) version 17.5.1.3 on vCMP Tenant.
  Covers the modern TMUI GUI (17.x) and full TMSH CLI + Bash. ALWAYS use this skill for
  any F5, BIG-IP, ASM, Advanced WAF, TMSH, WAF policy, attack signatures, bot defense,
  DoS protection, policy builder, blocking mode, transparent mode, false positive, support ID,
  event log, violation, URL/parameter/cookie/file-type entity, JSON/XML/GraphQL profile,
  brute force, credential stuffing, IP intelligence, geolocation, DataSync, datasync-global-dg,
  vCMP guest, tenant, or TMOS question. Also use when user asks why F5 is blocking traffic,
  how to allow a request, how to tune WAF policy, or any Advanced WAF troubleshooting task.
---

# F5 BIG-IP Advanced WAF — Version 17.5.1.3 (Build 0.0.19)
## Deployment: vCMP Tenant (BIG-IP Tenant)

---

## ⚠️ CRITICAL: GUI CONTEXT AWARENESS

Version 17.x uses the **modern Configuration Utility (TMUI)**. This is different from the legacy GUI in versions before 14.x.

**Modern GUI (17.5.x) characteristics:**
- Left navigation pane with expandable menus
- Main menu sections: Local Traffic, Security, Access, Network, System
- **Security > Application Security** is where ALL Advanced WAF policy work lives
- The old "Application Security" standalone menu was merged into **Security**
- Guided Configuration is under **Security > Guided Configuration**
- Event Logs are under **Security > Event Logs > Application > Requests**
- Bot Defense profiles are under **Security > Bot Defense**
- DoS Protection is under **Security > DoS Protection**
- IP Intelligence is under **Security > Network Firewall > IP Intelligence** (separate from WAF policy)

**Always confirm GUI path before answering.** If unsure, provide both the GUI path and the equivalent TMSH command.

---

## vCMP TENANT CONTEXT

On a vCMP system:
- The **vCMP Host** manages physical resources (blades, VLANs, resource allocation)
- **vCMP Guests (Tenants)** run their own full BIG-IP TMOS instance
- Advanced WAF must be provisioned as **Dedicated** on vCMP guests
- For best performance, use **remote syslog** for ASM logs rather than local logging
- **datasync-global-dg** device group is auto-created when Advanced WAF is provisioned — do NOT delete it
- Memory formula for guest: `(platform_memory - 3GB) × (cpus_assigned / total_cpus)`

**Checking vCMP guest status (from host):**
```bash
tmsh show sys cluster
tmsh show vcmp guest
tmsh show vcmp guest <guest-name> detail
```

**From inside the tenant (guest), treat it as a normal BIG-IP.**

---

## CLI REFERENCE (TMSH + Bash)

### Shell Navigation
```bash
# SSH login lands in Bash shell
tmsh                          # Enter TMOS Shell
exit                          # Back one level in TMSH
quit                          # Exit TMSH back to Bash
bash                          # Enter Bash from TMSH

# Prompt examples:
# Bash:  [admin@bigip-01:Active:Standalone] ~ #
# TMSH:  admin@(bigip-01)(cfg-sync Standalone)(Active)(/Common)(tmos)#
```

### System Information
```bash
tmsh show sys version
tmsh show sys hardware
tmsh show sys failover
tmsh show sys performance all-stats
tmsh show sys memory
tmsh show sys cpu
tmsh show sys clock
tmsh show sys log ltm | tail -50
```

### ASM / Advanced WAF — Core TMSH Commands

#### Policy Management
```bash
# List all ASM policies
tmsh list asm policy

# Show policy details
tmsh show asm policy <policy-name> detail

# Create a new policy (basic)
tmsh create asm policy <policy-name> protocol-independent true enforcement-mode blocking

# Apply/activate a policy
tmsh modify asm policy <policy-name> active

# Deactivate a policy
tmsh modify asm policy <policy-name> inactive

# Delete a policy
tmsh delete asm policy <policy-name>

# Apply pending changes (equivalent to "Apply Policy" in GUI)
tmsh modify asm policy <policy-name> apply-policy

# Save config
tmsh save sys config
```

#### Export / Import Policies
```bash
# Export policy to XML file
tmsh save asm policy <policy-name> xml-file /var/tmp/my-policy.xml

# Export policy to binary
tmsh save asm policy <policy-name> binary-file /var/tmp/my-policy.plc

# Import policy from XML
tmsh load asm policy <policy-name> xml-file /var/tmp/my-policy.xml

# Import declarative policy (AS3-style JSON)
tmsh load asm policy <policy-name> json-file /var/tmp/my-policy.json
```

#### Linking WAF Policy to Virtual Server
```bash
# Attach ASM policy to virtual server via LTM policy
tmsh list ltm virtual <vs-name> policies

# The recommended method is via LTM policy — check:
tmsh list ltm policy <ltm-policy-name> rules

# View virtual server security settings
tmsh list ltm virtual <vs-name> security-log-profiles
```

#### Attack Signatures
```bash
# Show signature update status
tmsh show asm signature-file-update

# List signature sets in a policy
tmsh list asm policy <policy-name> signature-sets

# Update signatures (trigger manual update)
tmsh run asm signature-update

# Show all signature sets
tmsh list asm signature-set
```

#### Violations & Requests (Event Log)
```bash
# View ASM event log from bash
cat /var/log/asm | tail -100

# Show recent blocked requests
grep "BLOCK" /var/log/asm | tail -50

# ASM process status
tmsh show sys service asm

# Check if ASM is ready
grep "ASM started" /var/log/asm
```

#### Bot Defense
```bash
# List bot defense profiles
tmsh list asm bot-defense profile

# Show bot defense profile details
tmsh show asm bot-defense profile <profile-name>

# Create a basic bot defense profile
tmsh create asm bot-defense profile <profile-name> mode blocking
```

#### DoS Protection
```bash
# List DoS profiles
tmsh list asm dos-detection

# Show DoS profile
tmsh show asm dos profile <profile-name>

# View current DoS statistics
tmsh show asm dos-protection
```

#### IP Intelligence
```bash
# Check IP Intelligence database status
tmsh show sys iprep-status

# List IP intelligence categories
tmsh list net ip-intelligence
```

#### Cookies
```bash
# List allowed cookies in a policy
tmsh list asm policy <policy-name> cookies

# Add allowed cookie
tmsh modify asm policy <policy-name> cookies add { <cookie-name> { type wildcard } }

# Important for upgrades: Add TS* wildcard cookie before upgrading to prevent cookie violations
tmsh modify asm policy <policy-name> cookies add { "TS*" { type wildcard } }
```

#### DataSync (HA Sync)
```bash
# Check device group sync status
tmsh show cm sync-status

# Show datasync-global-dg (NEVER delete this)
tmsh show cm device-group datasync-global-dg

# Force sync
tmsh run cm config-sync to-group <device-group-name>
```

---

## GUI WALKTHROUGH — MODERN TMUI (17.5.x)

### Accessing the Configuration Utility
- URL: `https://<management-ip>/`
- Default port: 443
- The GUI is also called **TMUI** (Traffic Management User Interface)

### WAF Policy Creation (GUI)
**Path:** Security > Application Security > Security Policies > Policies List > Create

Key fields:
- **Name**: Policy name
- **Policy Template**: Choose from Rapid Deployment, Fundamental, Comprehensive, or blank
- **Enforcement Mode**: Blocking or Transparent (start with Transparent for new policies)
- **Application Language**: UTF-8 (default)
- **Signature Staging**: Enabled by default (new signatures enter staging before enforcement)

### Guided Configuration (Quickest setup)
**Path:** Security > Guided Configuration > Web Application Protection

Walks through: Virtual Server, Pool, WAF Policy, Bot Defense, DoS Protection in a wizard.

### Viewing/Managing Violations
**Path:** Security > Event Logs > Application > Requests

Filters available:
- Support ID
- Violation Type
- Date/Time range
- IP address
- Username
- Request Status (Blocked / Alarmed / Passed)

**To accept an entity from request log:**
1. Click on a request in Event Logs > Application > Requests
2. Click on the violation
3. Click "Accept this suggestion" or go to the Suggestions page

### Policy Builder / Learning
**Path:** Security > Application Security > Policy Building > Traffic Learning

- Shows suggested entities: URLs, Parameters, File Types, Cookies
- Color-coded confidence score (5–100%)
- Accept or delete suggestions individually or in bulk
- Learning speed: Slow / Medium / Fast (controlled per entity type)

### Applying a Policy
Every time you make changes in the GUI, you MUST click **Apply Policy** (top right, yellow button) for changes to take effect.

**Equivalents:**
- GUI: "Apply Policy" button
- TMSH: `tmsh modify asm policy <name> apply-policy`

### Blocking Settings
**Path:** Security > Application Security > Security Policies > Policies List > [Policy Name] > Blocking Settings

Categories:
- **Evasion Techniques** — HTTP protocol violations used to evade detection
- **HTTP Protocol Compliance** — Enforce HTTP spec compliance
- **Web Scraping** — Detect scraping bots
- **Attack Signatures** — Core detection engine

Each setting has: **Learn / Alarm / Block** checkboxes (LAB model).

### Attack Signatures
**Path:** Security > Application Security > Attack Signatures > Attack Signature Sets

- Assign signature sets to a policy
- Per-signature override: Security > Application Security > Attack Signatures > Attack Signatures List
- Staging: New signatures default to staging (alarm-only) for 7 days before blocking

### Entity Management
```
URLs:           Security > Application Security > URLs > Allowed HTTP URLs
Parameters:     Security > Application Security > Parameters > Parameters List
File Types:     Security > Application Security > File Types > Allowed File Types
Cookies:        Security > Application Security > Cookies > Cookies List
Headers:        Security > Application Security > Headers
```

### Bot Defense Profile
**Path:** Security > Bot Defense > Bot Defense Profiles > Create

Modes:
- **Alarm**: Log bots, don't block
- **Block**: Block detected bots
- **Transparent**: Detect only, no action

Attach to virtual server: Local Traffic > Virtual Servers > [VS Name] > Security > Policies > Bot Defense Profile

### DoS Profile
**Path:** Security > DoS Protection > Protection Profiles > Create

- **Proactive Bot Defense** — Challenges before the attack
- **TPS-based Detection** — Transactions-per-second thresholds
- **Stress-based Detection** — Server stress metrics

### IP Intelligence
**Path:** Security > Network Firewall > IP Intelligence > Policies

Enable per-policy: Security > Application Security > [Policy] > Policy Properties > General Settings > IP Intelligence

### Login Page Configuration
**Path:** Security > Application Security > Sessions and Logins > Login Pages List

Required for:
- Brute Force protection
- Credential Stuffing detection
- Session tracking

---

## TROUBLESHOOTING

### Is ASM Running?
```bash
# Check ASM service
tmsh show sys service asm

# Check log for startup message
grep "ASM started" /var/log/asm

# Check ASM process
ps aux | grep asm

# BIG-IP displays "ASM is not ready" in GUI if still initializing
# Wait 5 minutes after provisioning level change before configuring
```

### Policy Not Blocking
```bash
# 1. Verify policy is ACTIVE (not inactive)
tmsh show asm policy <policy-name> | grep -i active

# 2. Verify policy is APPLIED (no pending changes)
tmsh show asm policy <policy-name> | grep -i "apply"

# 3. Check enforcement mode
tmsh list asm policy <policy-name> | grep enforcement-mode

# 4. Verify policy is attached to virtual server
tmsh list ltm virtual <vs-name>

# 5. Check if traffic matches the virtual server
tmsh show ltm virtual <vs-name>
```

### Unknown/Unexpected HTTP Response Status Code Blocking
```bash
# If ASM blocks due to unrecognized HTTP response status codes:
# Go to: Security > Application Security > HTTP Protocol Compliance > Response Codes
# Add the missing response code to the allowed list
# Then Apply Policy

# CLI equivalent: check response code settings
tmsh list asm policy <policy-name> | grep -i response
```

### Support ID Lookup
When a request is blocked, the user sees a Support ID. Use it to find the event:
```
GUI: Security > Event Logs > Application > Requests > Filter by Support ID
```
```bash
# From bash
grep "<support-id>" /var/log/asm
```

### High False Positives
1. Switch policy to **Transparent** mode temporarily
2. Review Traffic Learning suggestions with high confidence (>90%)
3. Accept legitimate entities
4. Switch back to **Blocking** mode
5. Use **Staging** for attack signatures to alarm before blocking

### Signature Update Issues
```bash
# Check last update time
tmsh show asm signature-file-update

# Check connectivity to F5 update servers
curl -v https://signatures.f5.com

# Manual update trigger
tmsh run asm signature-update

# Check logs
tail -f /var/log/asm
```

### Cookie Violations After Upgrade
Before upgrading BIG-IP:
1. Disable the "Modified domain cookie" violation in the policy
2. Add a wildcard cookie named `TS*` to allowed cookies
3. Re-enable the violation 24+ hours after upgrade
4. Sync cookie protection settings across all devices in the device group

---

## KEY LOG FILES

| Log | Path | Purpose |
|-----|------|---------|
| ASM/WAF events | `/var/log/asm` | All WAF decisions and errors |
| LTM | `/var/log/ltm` | Traffic management events |
| System | `/var/log/messages` | General system messages |
| Audit | `/var/log/audit` | Config changes |
| HTTP (ASM requests) | Stored in DB, view via GUI | Request-level details |

```bash
# Live tail of ASM log
tail -f /var/log/asm

# Filter for BLOCK decisions
grep "BLOCK" /var/log/asm | tail -100

# Filter for a specific IP
grep "10.10.10.5" /var/log/asm | tail -50

# Filter for a specific violation
grep "SQL injection" /var/log/asm | tail -50
```

---

## PROVISIONING (First-Time Setup)

```bash
# Check current provisioning
tmsh show sys provision

# Set Advanced WAF to Nominal (required for vCMP guests)
tmsh modify sys provision asm level nominal

# Save and wait 5 minutes
tmsh save sys config

# Verify ASM is ready
grep "ASM started" /var/log/asm
```

**⚠️ Wait 5 minutes after changing provisioning level. Do not make any WAF config changes until ASM reports ready.**

---

## REFERENCE FILES

For deeper topics, read:
- `references/gui-navigation-17x.md` — Full GUI menu map for version 17.x
- `references/tmsh-asm-commands.md` — Extended TMSH ASM command reference
- `references/policy-templates.md` — Policy template comparison (Rapid/Fundamental/Comprehensive)
- `references/vcmp-tenant.md` — vCMP Tenant-specific guidance
