# FMC 7.7.0 — VPN and Identity

Covers: site-to-site VPN, SD-WAN topology, remote access (RA) VPN, dynamic access policies
(DAP), identity sources/realms. GUI/API-configured; CLI is for verification only.

## Table of Contents
1. Site-to-site VPN
2. SD-WAN topology
3. Remote access VPN
4. Dynamic Access Policy (DAP)
5. Identity sources & realms
6. CLI verification

---

## 1. Site-to-site VPN

**GUI path (7.7.0 menu naming):** Secure Connections > Site-to-Site VPN & SD-WAN (older
menu naming: Devices > VPN > Site To Site).

- **Policy-based** (crypto map style) or **route-based** (VTI — virtual tunnel interface)
  topologies.
- Route-based VPNs: view VTI details (including dynamically created virtual access
  interfaces for dynamic VTIs) under Devices > Device Management > device > **Interfaces >
  Virtual Tunnels** tab.
- **SGT (Security Group Tag) propagation** over SVTI/DVTI (10.0.0, mention only if Omar is
  looking ahead to that version) — not present on 7.7.0.
- **BFD-based failover** and **ECMP hub load balancing** for dynamic VTIs are 10.0.0
  features — not on 7.7.0 either; if Omar asks about these, they require an upgrade path.

```bash
# FTD CLI verification:
show crypto ipsec sa
show crypto isakmp sa          # or "show crypto ikev2 sa" depending on IKE version
show vpn-sessiondb detail l2l  # site-to-site session detail
```

---

## 2. SD-WAN topology

**GUI path:** Secure Connections > Site-to-Site VPN & SD-WAN > **SD-WAN Topology** (wizard
introduced 7.6.0, applies on 7.7.0). Lets you build hub-and-spoke VPN topologies between HQ
and branch sites more easily than hand-building route-based VPN policies.

- Application performance monitoring for WAN interfaces: Insights & Reports (older naming:
  Overview) > **SD-WAN Summary** dashboard > Application Monitoring tab.

```bash
# FTD CLI verification (same commands as regular site-to-site, SD-WAN rides on top):
show crypto ipsec sa
show route
```

---

## 3. Remote access VPN

**GUI path:** Devices > **VPN > Remote Access**. Requires an SSL/IKEv2 connection profile,
group policy, address pool, and AnyConnect (or native OS client) configuration.

**7.7.0 new: Geolocation-based RA VPN.** Allow or block RA VPN connections by country/region
*before authentication*, with the blocked attempts logged for audit purposes.

**GUI path for geo restriction:** Objects > **Access List > Service Access** (define the
country/region-based restriction object), then reference it in the RA VPN connection profile
settings.

```bash
# FTD CLI verification:
show vpn-sessiondb detail ra-vpn
show vpn-sessiondb anyconnect
```

---

## 4. Dynamic Access Policy (DAP)

**GUI path:** Devices > **Dynamic Access Policy**. DAP lets you vary RA VPN access/permissions
based on endpoint posture (installed processes, files, registry keys, AV status, etc.)
evaluated at connection time.

**7.7.0 new:** easier configuration of **posture assessment criteria** directly in the DAP
UI — define file/process/registry endpoint attributes with unique endpoint IDs, then
reference those IDs when building DAP records, instead of hand-crafting the criteria each
time.

**GUI paths:**
- Define criteria: Devices > Dynamic Access Policy > Add/Edit Policy > **Posture Assessment
  Criteria**
- Use in a record: Devices > Dynamic Access Policy > Add/Edit Policy > Add/Edit DAP Record >
  **Advanced > Endpoint Criteria**

---

## 5. Identity sources & realms

**GUI path:** Integration > Other Integrations > **Realms** (for AD/LDAP/Azure AD directory
integration) and **Identity Sources** (for the active/passive authentication mechanism used
by Identity Policy rules).

Realm types relevant heading into/through 7.7.0:
- **Active Directory (AD) realm** — classic LDAP-based realm for passive/active auth.
- **SAML - Azure AD realm** — Azure AD for active authentication (captive portal via Azure
  AD login) and, combined with Cisco ISE, passive authentication (group data from Azure AD +
  session data from ISE).
- **Passive Identity Agent** for Microsoft AD (introduced 7.6.0) — a lightweight Windows
  agent sending AD login session data to FMC; supports FQDN/IPv4/IPv6 connectivity to FMC or
  Security Cloud Control, and both IPv4 and IPv6 user sessions.
- **pxGrid / Cisco ISE** integration for identity-based policy — correlate ISE-provided
  posture/identity with policy decisions. (Full **pxGrid Cloud** and **identity-based
  dynamic access control** combining ISE + Cisco Identity Intelligence are 10.0.0 features,
  not present on 7.7.0.)

**GUI path — configuring an Identity Policy** (to actually use realm data in ACP rules):
Policies > **Identity**. Reference the realm/identity source, then use user/group conditions
in your Access Control Policy rules.

**Easily configure an ISE identity source (7.6.0, still applies on 7.7.0):** the system can
use ISE ERS Operator credentials to log into the ISE Primary Authentication Node, download
certificates, and configure the identity source automatically instead of a fully manual
setup. Not supported for ISE-PIC.

```bash
# FTD CLI verification of identity/user data being applied (if needed):
show user-identity            # (naming/availability varies; primarily a FMC-side concern —
                                # check Analysis/Events & Logs > identity-related connection
                                # event fields for confirmation instead)
```

---

## 6. CLI verification

Most VPN/identity troubleshooting genuinely lives in the GUI (event viewer, VPN monitoring
dashboards) since the policy logic itself isn't CLI-configured. On the FTD CLI, the main
diagnostic commands are:

```bash
show vpn-sessiondb summary
show vpn-sessiondb detail l2l           # site-to-site
show vpn-sessiondb detail ra-vpn        # remote access
show crypto ipsec sa
show crypto isakmp sa
show route
packet-tracer input <ifc> tcp <src_ip> <src_port> <dst_ip> <dst_port>
```

For VPN troubleshooting syslogs specifically: since 7.6.0, all device troubleshooting
syslogs (not just VPN ones) can be sent to FMC — enable under Devices > Platform Settings >
Syslog > **Logging to Secure Firewall Management Center**, then view them under Devices >
**Troubleshooting Logs** (renamed from "Devices > VPN > Troubleshooting"), or in context with
other events via Analysis/Events & Logs > **Unified Events** (filter by the Troubleshoot
Events type).
