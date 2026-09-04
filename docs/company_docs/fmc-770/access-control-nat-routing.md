# FMC 7.7.0 — Access Control, NAT, Routing

Covers: access control policy (ACP), prefilter policy, NAT, static/dynamic routing, BGP,
policy-based routing (PBR). All of this is **GUI/API-configured** — there is no CLI command
to "create a rule"; the CLI is only used afterward to verify what got deployed.

## Table of Contents
1. Access control policy (ACP)
2. Prefilter policy
3. NAT
4. Static & dynamic routing
5. BGP
6. Policy-based routing (PBR)
7. Verifying deployed config from the CLI

---

## 1. Access control policy (ACP)

**GUI path:** Policies > Access Control > Access Control. Create/edit a policy, then **Add
Rule**. Rules match top-down, first match wins (like most firewalls).

Rule conditions available: zones, networks, VLAN tags, users/groups (via Identity Policy),
applications (App-ID via Snort 3), URLs/categories, ports, and (7.7.0) an **Application
Default** option that limits an app-based rule to that app's default ports only (vs "Any
port," the old default behavior) — edit existing app-based rules after upgrade if you want
this tighter behavior, since upgrade leaves existing rules on "Any port."

Rule actions: Allow, Trust, Monitor, Block, Block with reset, Interactive Block (captive
portal-style). Allow/Trust rules can attach an **Intrusion Policy**, **File/Malware Policy**,
**Variable Set**, and logging settings.

**7.7.0 specific:**
- **Legacy ACP UI is fully removed** — the "Switch to Legacy UI" toggle is gone. If you're
  following an old screenshot/walkthrough referencing the legacy interface, it no longer
  applies.
- **New "Pending Rule Match" connection event reason** — marks connections that ended before
  matching any ACP rule (useful when troubleshooting "missing" connection events).
- **EVE (Encrypted Visibility Engine)** is increasingly tied into ACP advanced settings — see
  `references/intrusion-malware-decryption.md` for EVE exceptions, dashboard, and tuning.

```
# Typical click path for a new allow rule:
Policies > Access Control > Access Control > <policy> > Add Rule
  Name, Action=Allow, Zones, Networks, Ports/Applications as needed
  Inspection tab: Intrusion Policy + Variable Set, File Policy
  Logging tab: Log at Beginning/End of Connection (or both)
  Save > Save (top of policy) > Deploy
```

---

## 2. Prefilter policy

Runs *before* the ACP, operating on outer headers only (no deep inspection) — used for fast
trust/block decisions or to handle traffic that the standard ACP can't (e.g., tunneled
protocols, very high-throughput flows you want to bypass Snort entirely).

**GUI path:** Policies > Access Control > Prefilter.
- **Dynamic flow offload** (extended to Secure Firewall 3100/4200 in 7.7.0, was previously
  4100/9300-only) lets qualifying long-lived flows be offloaded to hardware after initial
  inspection — enabled by default on new/upgraded deployments, not supported with container
  instances.

---

## 3. NAT

**GUI path:** Devices > NAT > (select or create a NAT policy assigned to your device(s)).
- **Auto NAT** rules: simple object-based, generated per network/host object.
- **Manual NAT** rules: ordered, more control over translation and bidirectionality.
- You can create network groups directly while editing a NAT rule (since 7.2.6) instead of
  pre-creating the object separately.
- **Recovery-config mode** (7.7.0, see device-management-ha.md) supports emergency NAT and
  object-group changes directly at the FTD CLI when management connectivity is down — those
  changes then show up as out-of-band drift to reconcile in the GUI afterward.

```bash
# FTD CLI verification after deploy:
show nat
show nat detail
show xlate                    # active translations
```

---

## 4. Static & dynamic routing

**GUI path:** Devices > Device Management > device > **Routing** tab.
- Static routes: Routing > Static Route.
- Dynamic protocols: OSPF, OSPFv3, EIGRP, BGP — each gets its own sub-tab under Routing.
- VRF-aware interfaces (user-defined Virtual Routing and Forwarding) support routing, AAA,
  and device management services (NetFlow, SSH, SNMP, syslog) independently per VRF since
  7.4.1/7.6.0.

```bash
# FTD CLI verification:
show route
show route ospf
show ipv6 nd summary           # IPv6 neighbor discovery
show ipv6 nd detail
```

---

## 5. BGP

**GUI path:** Devices > Device Management > device > Routing > **BGP** (IPv4 or IPv6) >
Neighbor configuration.

**BGP AS-Override** (new in 7.6.1, applicable on 7.7.0): lets FTD overwrite a received
peer ASN with its own, so downstream routers don't reject the prefix as a routing loop based
on AS_PATH content. Configure under: Add/Edit Neighbor > **AS Override**.

```bash
# FTD CLI verification:
show bgp summary
show bgp neighbors
```

---

## 6. Policy-based routing (PBR)

**GUI path:** Devices > Device Management > device > Routing > **Policy Based Routing**, or
configured via an extended ACL referenced from a PBR policy.

**7.7.0 added:** PBR can route based on **user-defined domains** — create a basic custom
application detector with your domain pattern(s) and an NSG (network service group) tag,
reference it in an extended ACL, and use that ACL in your PBR policy. (Advanced custom
detectors using uploaded Lua files came later, in 10.0.0 — not available on 7.7.0.)

```
Devices > Device Management > device > Routing > Policy Based Routing > Add Policy
  Add a match ACL (built from your custom app/domain object) > set egress interface(s)
```

---

## 7. Verifying deployed config from the CLI

After any policy change + Deploy, the source of truth on the device is its running-config:

```bash
show running-config                 # full deployed config
show running-config access-list
show running-config nat
show running-config route
show access-list                    # hit counts per ACE
show conn                           # active connections (useful to confirm a rule is matching)
packet-tracer input <ifc> tcp <src_ip> <src_port> <dst_ip> <dst_port>
                                     # simulate a packet through the full policy pipeline —
                                     # the single best tool for "why isn't my rule working"
```
