# vCMP Tenant — BIG-IP Advanced WAF Specific Guidance

## Architecture Overview

```
Physical Hardware (VELOS / iSeries / VIPRION)
└── vCMP Host (F5OS or BIG-IP Host layer)
    ├── vCMP Guest 1 (Tenant) ← You are here
    │   ├── Full BIG-IP TMOS 17.5.1.3
    │   ├── Advanced WAF (ASM)
    │   └── LTM
    ├── vCMP Guest 2 (Tenant)
    └── vCMP Guest 3 (Tenant)
```

## Key Rules for vCMP + Advanced WAF

1. **Advanced WAF should be provisioned as Dedicated** on vCMP guests
   - Never provision as Nominal on a vCMP guest unless memory permits
   - Check: `tmsh show sys provision asm`

2. **Memory is shared** — calculate guest memory before provisioning WAF
   - Formula: `(platform_memory - 3GB) × (cpus_assigned / total_cpus)`

3. **Use remote syslog** for ASM logs, not local logging
   - Local logging on a vCMP guest creates I/O pressure on shared storage
   - Configure: System > Logs > Configuration > Log Publishers

4. **datasync-global-dg is auto-created** — do NOT delete it
   - Created even if no HA device groups exist
   - Syncs client-side scripts and crypto keys across trust domain

## Checking vCMP Context

From inside the guest (tenant), everything looks like a normal BIG-IP:
```bash
# Verify you are in a vCMP guest
tmsh show sys hardware | grep -i vcmp
# Or check:
cat /VERSION | grep -i Platform
```

From the vCMP host (if accessible):
```bash
tmsh show vcmp guest
tmsh show vcmp guest <guest-name> detail
tmsh show vcmp guest <guest-name> stats
```

## Resource Allocation on vCMP

```bash
# From HOST: check guest resource allocation
tmsh list vcmp guest <guest-name>

# From GUEST: check your provisioned memory
tmsh show sys memory

# From GUEST: check CPU allocation
tmsh show sys performance all-stats | grep -i cpu
```

## Network Configuration on vCMP

VLANs must be assigned to the guest by the vCMP host admin.
From the guest, you only see VLANs that were assigned to it.

```bash
# List available VLANs (as seen from guest)
tmsh list net vlan

# List self IPs
tmsh list net self

# Check trunk/interface status
tmsh show net interface
```

## Provisioning Advanced WAF on vCMP Guest

```bash
# Check current provisioning
tmsh show sys provision

# Set ASM to Dedicated (recommended for vCMP)
tmsh modify sys provision asm level dedicated

# OR Nominal if memory is tight
tmsh modify sys provision asm level nominal

# Save and wait 5 minutes
tmsh save sys config

# Monitor ASM startup
tail -f /var/log/asm
# Look for: "ASM started successfully"
```

## HA on vCMP Guests

HA (High Availability) is configured between vCMP guests, not between hosts.
The guests form their own HA pair (Active/Standby).

```bash
# Check HA state from inside guest
tmsh show sys failover
tmsh show cm sync-status
tmsh show cm failover-status

# Force failover (from Active)
tmsh run sys failover standby

# Sync configuration to peer
tmsh run cm config-sync to-group <device-group-name>
```

## Software Upgrade on vCMP Guest

Upgrades are done per-guest, not at the host level.

```bash
# From guest: check installed software
tmsh show sys software

# List boot locations
tmsh show sys software status

# Install new version (requires ISO on the system)
tmsh install sys software image BIG-IP-17.5.1.3-0.0.19.iso volume HD1.2

# Activate new volume
tmsh run sys software status
tmsh modify sys software volume HD1.2 active { base-build-on-disk true }
```

## Common vCMP + WAF Issues

### Issue: ASM not starting on guest
**Cause:** Insufficient memory allocated to guest
**Fix:**
1. Increase CPU/memory allocation from vCMP host
2. Reduce other module provisioning on the guest
3. Use Nominal instead of Dedicated if memory is very limited

### Issue: High latency on WAF inspection
**Cause:** CPU contention between vCMP guests
**Fix:**
- Check CPU pinning from vCMP host
- Reduce other guests' CPU allocation
- Use `tmsh show sys performance all-stats` to monitor

### Issue: Logs not appearing in GUI
**Cause:** Local logging I/O pressure, or log profile not attached
**Fix:**
1. Verify log profile is attached to virtual server
2. Switch to remote syslog for ASM events
3. Check: `tmsh show sys service asm`

### Issue: DataSync device group conflicts
**Cause:** datasync-global-dg misconfiguration
**Fix:** Never delete or modify this group. If corrupted:
```bash
# Check group status
tmsh show cm device-group datasync-global-dg
# Re-sync
tmsh run cm config-sync to-group datasync-global-dg
```
