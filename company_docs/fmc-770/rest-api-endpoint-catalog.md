# FMC 7.7.0 — REST API Endpoint Catalog (What Every Call Does)

This is the **complete map of the FMC 7.7.0 REST API surface** — every resource group Cisco
documents, the HTTP verbs each supports, and what job each one actually performs. Use this
when the user asks "can the API do X" or "what's the endpoint for X" — check here before
guessing at a URL. Pair with `rest-api-automation.md` for authentication and worked examples.

**Base URL for everything below** (unless a table says otherwise):
```
https://<fmc-ip>/api/fmc_config/v1/domain/<DOMAIN_UUID>/<category>/<resource>
```
A few categories live under different roots — noted explicitly: `fmc_platform` (auth, users,
audit), `fmc_troubleshoot` (packet tracer, RADKit, profiling), `fmc_netmap` (network map/host
discovery data).

**Verb meaning, every table:** GET = read one object by ID · GETALL = read/list all objects
of that type (supports `offset`/`limit`/`expanded` paging, often `filter`) · POST = create ·
PUT = update/replace · DELETE = remove. Not all resources support all five.

## Table of Contents
1. Object Services — reusable config building blocks
2. Policy Services — the actual security/access policies
3. Device Services — per-device settings pushed by policy
4. Device Management (records, groups, HA pairs, clusters, templates)
5. Deployment Services — pushing changes to devices
6. Health Services — monitoring & alerting
7. Chassis Services — FXOS-level (4100/9300, 3100/4200)
8. Troubleshoot Services — packet tracer, captures, profiling, RADKit
9. Network Map & Analysis — discovery data, active sessions, identity
10. Audit, Change Management, Users — governance & RBAC
11. Integration, Intelligence, License, Search, System, Updates

---

## 1. Object Services

Path root: `/object/<resource>`. These are the reusable building blocks referenced by
policies (networks, hosts, ports, certificates, VPN crypto proposals, security zones, realms,
etc.) — basically everything under the FMC GUI's **Objects > Object Management** tree.

| Resource | Verbs | Job |
|---|---|---|
| `networks`, `hosts`, `ranges`, `fqdns` | full CRUD | IP/network/FQDN objects used across ACP, NAT, routing |
| `networkgroups` | full CRUD | Group multiple network/host objects together |
| `ports`, `protocolportobjects`, `portobjectgroups`, `anyprotocolportobjects` | read/CRUD | Port and protocol objects, and groups of them |
| `icmpv4objects`, `icmpv6objects` | full CRUD | ICMP type/code objects for rules |
| `securityzones`, `interfacegroups`, `interfaceobjects` | CRUD/read | Zone-based rule matching objects |
| `vlantags`, `vlangrouptags` | full CRUD | VLAN tag objects/groups for rule matching |
| `geolocations`, `countries`, `continents` | read/CRUD | Country/region objects for geo-based rules (e.g., RA VPN geolocation blocking) |
| `applications`, `applicationfilters`, `applicationgroups`, `applicationcategories`, `applicationrisks`, `applicationproductivities`, `applicationtags`, `applicationtypes` | mostly read + CRUD on filters/groups | App-ID catalog and custom application filter/group objects for ACP rules |
| `urls`, `urlgroups`, `urlcategories` | full CRUD (categories read-only) | URL and URL-category objects for web filtering rules |
| `filecategories`, `filetypes` | read | Reference data for file/malware policy rule conditions |
| `certenrollments`, `internalcas`, `internalcertificates`, `externalcertificates`, `externalcacertificates`, `certificatemaps` | full CRUD | PKI trustpoints and certificates — VPN, ACME, SSL decryption, RA VPN auth |
| `ikev1policies`, `ikev1ipsecproposals`, `ikev2policies`, `ikev2ipsecproposals` | full CRUD | IKE/IPsec crypto proposal objects for VPN tunnels |
| `radiusservergroups`, `dnsservergroups`, `ntpservers`, `sshaccesssettings` (see also Policy Services) | full CRUD | AAA/infrastructure server-group objects |
| `realms`, `localrealmusers`, `realmusers`, `realmusergroups`, `azureadrealms` | full CRUD | Identity realm objects (AD/LDAP/Azure AD) and their users/groups |
| `securitygrouptags`, `isesecuritygrouptags` | full CRUD / read | SGT objects for TrustSec-aware rules |
| `dynamicobjects`, `dynamicobjectmappings`, `bulkdynamicobjects` | full CRUD | Dynamic Attribute Connector objects (cloud/workload-driven group membership) |
| `sinkholes`, `sidnsfeeds`, `sidnslists`, `sinetworkfeeds`, `sinetworklists`, `siurlfeeds`, `siurllists`, `customsiiplists`, `customsiurllists` | full CRUD / read | Security Intelligence feeds/lists (DNS, network, URL) for SI-based blocking |
| `intrusionrules`, `intrusionrulegroups` | full CRUD | Custom Snort intrusion rules and groupings; `intrusionrulesupload` (POST) imports rule files |
| `standardaccesslists`, `extendedaccesslists`, `standardcommunitylists`, `expandedcommunitylists`, `extendedcommunitylists`, `aspathlists`, `ipv4prefixlists`, `ipv6prefixlists`, `routemaps` | full CRUD | Routing-policy match objects (BGP/OSPF route-maps, prefix/community/AS-path lists) |
| `ipv4addresspools`, `ipv6addresspools`, `dhcpipv6pools`, `macaddresspools` | full CRUD | Address pools for RA VPN, DHCP, cluster MAC assignment |
| `grouppolicies`, `secureclientcustomizations`, `anyconnectpackages`, `anyconnectprofiles`, `anyconnectcustomattributes`, `anyconnectexternalbrowserpackages`, `hostscanpackages` | full CRUD | RA VPN client (AnyConnect/Secure Client) group policies, packages, profiles |
| `serviceaccessobjects`, `serviceaccessobjectsoverrides` | full CRUD / read | Geolocation-based service access restriction objects (RA VPN geo blocking) |
| `distinguishednames`, `distinguishednamegroups` | read/CRUD | X.500 DN objects used in decryption rule matching |
| `variables`, `variablesets` | full CRUD / read | Intrusion policy variable sets (`$HOME_NET`, `$EXTERNAL_NET`, etc.) |
| `timeranges`, `timezoneobjects`, `globaltimezones` | full CRUD / read | Time-based rule objects |
| `keychains` | full CRUD | Routing protocol authentication key chains |
| `tunneltags` | full CRUD | VPN tunnel tagging objects |
| `endpointdevicetypes` | read | Reference data for DAP endpoint criteria |
| `umbrellaprotectionpolicies` | read/POST | Umbrella DNS protection policy objects |

---

## 2. Policy Services

Path root: `/policy/<resource>`. These are the actual **policies** you assign to devices —
this is the API-equivalent of everything under Policies/Devices in the GUI.

| Resource | Verbs | Job |
|---|---|---|
| `accesspolicies` + `accessrules` (supports `?bulk=true`, up to 1000 rules per call) | full CRUD | Access Control Policy and its rules — the core allow/block/inspect logic |
| `prefilterpolicies` + `prefilterrules`, `prefilter/defaultactions`, `prefilter/hitcounts` | full CRUD / read | Prefilter policy (pre-Snort fastpath/block/tunnel rules) and rule hit counters |
| `ftdnatpolicies` + `autonatrules`, `manualnatrules`, `natrules` (read), `natexemptrules` (read) | full CRUD | NAT policy and its auto/manual rules |
| `intrusionpolicies`, `intrusionrulegroups` (policy-scoped), `networkanalysispolicies` | full CRUD | IPS (Snort) policies and Network Analysis Policies (preprocessing tuning) |
| `filepolicies` + `filerules` | full CRUD | Malware & File policy and its rules |
| `decryptionpolicies` + `decryptionpolicyrules` | full CRUD | TLS/SSL decryption policy and rules |
| `identitypolicies` | read (config via GUI/wizard) | Identity policy tying realms to active/passive authentication rules |
| `dnspolicies`, `dnssettings`, `allowdnsrules`, `blockdnsrules` | read/CRUD | DNS policy — allow/block DNS resolution based on SI/category |
| `umbrelladnspolicies` + `umbrelladnsrules` | full CRUD | Cisco Umbrella DNS-layer policy integration |
| `healthpolicies` | full CRUD | Health monitor alerting policy (which modules alert, thresholds) |
| `ftdplatformsettingspolicies` (+ nested: `eventlists`, `ftd dnssettings`, `ftd syslogsettings`, `icmpsettings`, `bannersettings`, `loggingsettings`, `snmpsettings`, `sshaccesssettings`, `sshclientsettings`, `sshserversettings`, `ntpsettings`, `timesynchronizationsettings`, `timezonesettings`, `syslogalerts`, `syslogids`, `httpaccesssettings`, `loggingdestinations`, `loggingemailsetups`, `basicloggingsetups`, `trusteddnssettings`) | full CRUD | FTD Platform Settings policy — device-level system config (SSH/HTTPS access, SNMP, syslog, NTP, banners) |
| `chassisplatformsettingspolicies` | full CRUD | Chassis-level (FXOS) platform settings for 4100/9300 |
| `flexconfigpolicies` | read/POST | FlexConfig policies (legacy CLI-injection config not yet natively supported) |
| `ravpns` + `connectionprofiles` | full CRUD | Remote Access VPN policy and its connection profiles |
| `ftds2svpns`, `s2svpnsummaries`, `ipsecsettings`, `ipsecadvancedsettings`, `ipseccryptomaps`, `ikesettings`, `loadbalancesettings` | full CRUD / read | Site-to-site VPN topologies and their IPsec/IKE settings |
| `zero trust applications`, `zerotrustpolicies` | full CRUD | Zero Trust Application Access (ZTNA/universal ZTNA) policy and app definitions |
| `dynamicaccesspolicies` | full CRUD | Dynamic Access Policy (DAP) for RA VPN posture-based access |
| `securityintelligencepolicies` | read | Security Intelligence policy status (feeds are objects; policy attaches them to ACP) |
| `netflowpolicies` | read/CRUD | NetFlow export policy |
| `snmpalerts` | read | SNMP alerting configuration |
| `ldapattributemaps` | read/CRUD | LDAP attribute mapping for identity/AAA |
| `policylists`, `policylocks` | full CRUD / POST | Policy list metadata; `policylocks` explicitly locks a policy during editing (concurrency control) |
| `hitcounts` | read/PUT | Access rule hit counters (how many times a rule matched — great for cleanup/audits) |
| `advancedsettings`, `defaultactions`, `inheritancesettings`, `addressassignmentsettings`, `accesslistsettings` | read/CRUD | Various policy-level advanced/default settings |
| `migrate` | POST | Policy migration helper (e.g., ASA config migration workflows) |

---

## 3. Device Services (per-device configuration pushed by policy)

Path root: `/devices/devicerecords/{deviceUUID}/<resource>`. These represent the **live,
per-device configuration** — interfaces, routing, DHCP — that gets compiled into what's
actually deployed to that FTD.

| Resource | Verbs | Job |
|---|---|---|
| `physicalinterfaces`, `subinterfaces`, `redundantinterfaces`, `etherchannelinterfaces`, `vlaninterfaces`, `bridgegroupinterfaces`, `loopbackinterfaces`, `vniinterfaces`, `virtualtunnelinterfaces` (VTIs) | full CRUD (some read-only for physical) | Every interface type configurable on the device |
| `fpphysicalinterfaces`, `fplogicalinterfaces`, `ftdallinterfaces`, `fpinterfacestatistics` | read/CRUD | Firepower-chassis-level interface views and stats (multi-instance/clustered contexts) |
| `virtualrouters`, `virtualswitches` | full CRUD | VRF-aware routing/switching contexts on the device |
| `ipv4staticroutes`, `ipv6staticroutes`, `staticroutes` (read-all) | full CRUD | Static routing table entries |
| `ospfinterface`, `ospfv2routes`, `ospfv3interfaces`, `ospfv3routes` | full CRUD | OSPFv2/v3 routing process and interface config |
| `bgp`, `bgpgeneralsettings` | full CRUD | BGP neighbor/AS config and general BGP settings (AS-Override, etc.) |
| `eigrproutes` | full CRUD | EIGRP routing config |
| `policybasedroutes` | full CRUD | PBR policies on the device |
| `bfdpolicies`, `bfdtemplates` | full CRUD | Bidirectional Forwarding Detection for fast link-failure routing convergence |
| `ecmpzones` | full CRUD | Equal-Cost Multi-Path routing zones |
| `dhcprelaysettings`, `dhcpserver` | full CRUD | DHCP relay and local DHCP server config on device interfaces |
| `ddnssettings` / `dynamicdnssettings` | read/PUT | Dynamic DNS registration for the device |
| `vteppolicies` | full CRUD | VXLAN tunnel endpoint policies |
| `inlinesets` | full CRUD | Inline (IPS-only, bump-in-the-wire) interface pair sets |
| `interfaceevents` | GETALL/POST | Interface state change events |
| `outofbandchanges` | GETALL/POST | **7.7.0**: retrieves/acknowledges out-of-band config drift detected after `recovery-config` emergency changes — the API equivalent of Devices > Health > Out of Band Status |
| `devicesettings` / `domain_devicesettings` | read/PUT | General per-device settings |
| `commands` | GETALL | Available CLI-style commands exposed for the device via API |
| `bulkregistrations` | POST | Register multiple devices to FMC in one call |
| `changemanagers` | POST | Change which FMC manages a device (manager reassignment) |
| `copyconfigrequests` | POST | Copy configuration from one device to another |
| `modelmigrations` | POST | Trigger a device model migration (e.g., Firepower → Secure Firewall hardware) |
| `exports` / `imports` | POST | Export/import device configuration bundles |
| `downloadsamplecsv` | GETALL | Sample CSV templates (e.g., for bulk static route import) |
| `managementconvergencemode` | GETALL/POST | Manages the mgmt-interface convergence mode setting |
| `metrics` (device-scoped) | GETALL | Device-level performance metrics |
| `ltpdevicerecords` | read | Low-Touch Provisioning (zero-touch) device records |

---

## 4. Device Management (records, groups, HA pairs, clusters, templates)

| Resource | Path root | Verbs | Job |
|---|---|---|---|
| `devicerecords` | `/devices/devicerecords` | full CRUD | The device registration record itself — add, view, edit, **unregister** (DELETE) a managed FTD |
| `devicegrouprecords` | `/devicegroups/devicegrouprecords` | full CRUD | Logical device groups (for organizing devices in the GUI/policy assignment) |
| `ftddevicehapairs` | `/devicehapairs/ftddevicehapairs` | full CRUD | Create/break FTD HA pairs; nested `monitoredinterfaces`, `failoverinterfacemacaddressconfigs` |
| `ftddevicecluster` | `/deviceclusters/ftddevicecluster` | full CRUD | Create/modify/delete FTD clusters; `ftdclusterreadinesscheck` (POST) validates before bootstrapping; `ftdclusterdevicecommands` (POST) issues enable/disable/control commands to cluster nodes; `clusterhealthmonitorsettings` tunes cluster health checks |
| `devicetemplates` | `/templates/devicetemplates` | full CRUD | Device Templates for zero-touch branch provisioning; `apply` (POST) pushes a template to devices; `generatetemplate` (POST) builds a template from an existing device; `templateinterfaces`, `modelmappings`, `vpnsettings`, `objectoverrides`, `variables`, `associations` manage template internals |
| `supporteddevicemodels` | `/templates/supporteddevicemodels` | read | Which hardware models support templating |

---

## 5. Deployment Services

Path root: `/deployment/<resource>`. This is the API path to **push configuration changes to
devices** — the equivalent of clicking "Deploy" in the GUI, plus rollback and change-review.

| Resource | Verbs | Job |
|---|---|---|
| `deployabledevices` | GETALL | List devices with pending (undeployed) configuration changes — check this before deploying |
| `deploymentrequests` | POST | **Trigger a deploy** to one or more devices — the core automation call |
| `deployments` | GETALL | Deployment history for a specific device (time-ranged) |
| `pendingchanges` | GETALL | Diff of exactly what policy/object changes are queued for deploy |
| `pendingchangesrequests` | POST | Generate a pending-changes report (policy diff and/or CLI diff) without deploying |
| `rollbackrequests` | POST | **Roll back** a device to a previous deployed configuration |
| `jobhistories` | GET/GETALL/PUT | Deployment job status/history; filter by device, time range, status (DEPLOYING/DEPLOYED/FAILED/ABORTED), or job type (DEPLOYMENT/ROLLBACK/CERTIFICATE) |
| `downloadreports` / `emailreports` | GETALL / POST | Download or email a deployment job's change report |
| `taskstatuses` | GETALL | Generic async task status polling (many long-running API calls return a task you poll here) |

**Typical automation pattern:** POST an object/policy change → GET `deployabledevices` to
confirm the device is now flagged out of date → POST `deploymentrequests` with the device
ID(s) → poll `jobhistories`/`taskstatuses` until status is `DEPLOYED`.

---

## 6. Health Services

Path root: `/health/<resource>`. Monitoring data — mirrors System/Administration > Health in
the GUI.

| Resource | Verbs | Job |
|---|---|---|
| `alerts` | GETALL | Active health alerts across FMC and managed devices |
| `metrics`, `aggregatemetrics` | GETALL | Raw and aggregated health metrics (CPU, memory, disk, connections, etc.) |
| `events` | GETALL | Health-related events |
| `pathmonitoredinterfaces` | GETALL | SLA/path-monitored interface status |
| `tunnelstatuses`, `tunnelsummaries`, `tunneldetails` | GET/GETALL | VPN tunnel up/down status and details — good for a scripted VPN dashboard |
| `ravpngateways` | GETALL | RA VPN gateway status |
| `terminateravpnsessions` | POST | **Force-disconnect** an active RA VPN session — useful for incident response |
| List of Health Modules | GETALL | Enumerates every available health module (for building custom health policies) |

---

## 7. Chassis Services

Path root: `/fmc_config/v1/domain/{domainUUID}/chassis/...` (FXOS-managed hardware: Firepower
4100/9300, Secure Firewall 3100/4200/6100 chassis layer). Mirrors the Chassis Manager /
`Devices > Device Management` chassis view.

| Resource | Verbs | Job |
|---|---|---|
| `fmcmanagedchassis` | GET/GETALL | List/inspect FXOS chassis managed by this FMC |
| `logicaldevices` | full CRUD | Logical device instances on a chassis (application instances) |
| `physicalinterfaces`, `etherchannelinterfaces`, `subinterfaces`, `networkmodules` | full CRUD | Chassis-level physical/logical interface and network module config |
| `chassisinterfaces`, `chassisinterfaceevents` | GET/GETALL/POST | Chassis interface state and events |
| `breakoutinterfaces` | POST | Break a high-speed port into multiple lower-speed ports |
| `joininterfaces` | POST | Rejoin previously broken-out interfaces |
| `snmpsettings` | full CRUD | Chassis-level SNMP config |
| `switchmode`, `switchmodereadinesscheck` | POST | Convert chassis between appliance and multi-instance mode, with a pre-check |
| `syncnetworkmodule` | PUT | Re-sync a network module's state with FMC |
| `faultsummary`, `evaluateoperation`, `instancesummary`, `interfacesummary`, `inventorysummary` | GETALL | Chassis health/inventory summaries |
| `appinfo` | GETALL | FXOS application version info |

---

## 8. Troubleshoot Services

Path root: `/fmc_troubleshoot/v1/domain/{domainUUID}/<resource>` — **note the different API
root** (`fmc_troubleshoot`, not `fmc_config`).

| Resource | Verbs | Job |
|---|---|---|
| `packettracer/traces` | POST | Run `packet-tracer` against an FTD or cluster via API and get the full result |
| `packettracer/pcaptraces` | POST | Run packet tracer using an uploaded PCAP as input |
| `packettracer/files` | GET/GETALL/POST/DELETE | Manage PCAP files stored on FMC for tracing/replay |
| `packettracer/files/{name}/details` | GETALL | Inspect packet-level details inside a stored PCAP |
| `cpuprofiler/{containerUUID}/modules` | GET/GETALL/POST | Snort 3 CPU profiling data per module — API access to the same data behind Devices > Troubleshoot > Snort 3 Profiling |
| `snortprofiler/{containerUUID}/rules` | GET/GETALL/POST | Snort rule-level performance profiling data |
| `radkit/services` | GET/GETALL/POST | **7.7.0**: manage the RADKit remote-support service registration from the API |
| `troubleshoot/device` | POST | Trigger a full troubleshoot bundle generation for Secure Firewall 3100/4200 chassis |

---

## 9. Network Map & Analysis

**Network Map** — path root `/fmc_netmap/v1/domain/{domainUUID}/<resource>` (discovery data):

| Resource | Verbs | Job |
|---|---|---|
| `hosts` | full CRUD (DELETE supports bulk+filter) | Hosts discovered/tracked in the network map (passive discovery data) |
| `vulns` | full CRUD (DELETE supports bulk+filter) | Vulnerability data associated with discovered hosts |

**Analysis** — path root `/fmc_config/v1/domain/{domainUUID}/analysis/<resource>` (identity &
session data):

| Resource | Verbs | Job |
|---|---|---|
| `activesessions` | GETALL / DELETE (bulk) | Currently active identity/user sessions; DELETE force-logs-out a session — rich filtering by user, IP, VPN attributes, realm, etc. |
| `identifiedusers` | GETALL / DELETE (bulk) | Users FMC has identified via realms/agents; DELETE purges user records |
| `useractivity` | GETALL / DELETE (bulk) | Log of identity-related activity/events |

---

## 10. Audit, Change Management, Users

**Audit Services** — root `/fmc_platform/v1/domain/{domainUUID}/audit/<resource>`:

| Resource | Verbs | Job |
|---|---|---|
| `auditrecords` | GET/GETALL | Every admin action logged on FMC — who did what, when |
| `configchanges` | GETALL | Configuration change details tied to a specific audit log/snapshot entry |

**Change Management** — root `/fmc_config/v1/domain/{domainUUID}/changemanagement/<resource>`
(the ticket-based approval workflow):

| Resource | Verbs | Job |
|---|---|---|
| `tickets` | GET/GETALL/POST/PUT | Create/view/update change-management tickets that gate policy edits |
| `previewchanges` | GETALL | Preview exactly what a ticket's changes will do before approval |
| `validationresults` | GETALL | Validation results (conflicts, errors) for a ticket's proposed changes |

**Users** — root `/fmc_config/v1/domain/{domainUUID}/users/<resource>`:

| Resource | Verbs | Job |
|---|---|---|
| `users` | GET/GETALL | List/inspect FMC internal (GUI) user accounts |
| `authroles` | GETALL | List all RBAC roles defined on FMC (Administrator, Security Analyst, etc.) |
| `duoconfigs` | GET/GETALL/PUT | Cisco Duo MFA integration settings |
| `ssoconfigs` | GET/GETALL/PUT | SAML SSO configuration for FMC GUI login |

---

## 11. Integration, Intelligence, License, Search, System, Update Packages

**Integration Services** — root `/fmc_config/v1/domain/{domainUUID}/integration/<resource>`:

| Resource | Verbs | Job |
|---|---|---|
| `cloudeventsconfigs`, `cloudintegrations`, `cloudregions`, `fmchastatuses` | read/CRUD | Security Cloud Control / cloud integration config and status |
| `umbrellaconnections`, `testumbrellaconnections` | full CRUD / POST | Cisco Umbrella integration setup and connection testing |
| `externallookups`, `externalstorage` | full CRUD | External data lookup sources and storage integration (e.g., syslog/SIEM export targets) |
| `configure` | GET/GETALL/POST | Generic integration configuration entrypoint |
| `refreshsecurexconfigs` | POST | Refresh SecureX/Security Cloud integration tokens/config |
| `datacenters` | GETALL | Cloud datacenter/region info |
| `tunneldeployments` | GET/POST | Cloud tunnel deployment management (e.g., cloud-delivered VPN scenarios) |
| `transcripts`, `tsdbupload` | GET / POST | Diagnostic transcript retrieval and telemetry DB upload (support-oriented) |
| `status` | GETALL | Overall integration status summary |

**Intelligence Services** — root `/fmc_tid/v1/domain/{domainUUID}/tid/<resource>` (Threat
Intelligence Director):

| Resource | Verbs | Job |
|---|---|---|
| `source` | full CRUD | Threat intel feed sources (STIX/TAXII, flat file, etc.) |
| `indicator`, `observable`, `incident` | GET/GETALL/PUT | TID indicators, observables, and incidents — read and update disposition (e.g., allowlist/blocklist status — field renamed from "whitelist" as of 7.1) |
| `element` | GET/GETALL | Generic TID data element lookup |
| `settings` | GET/PUT | TID global settings |
| `collections`, `discoveryinfo` | POST | Trigger TID collection jobs / discovery info gathering |

**License** — root `/fmc_config/v1/domain/{domainUUID}/license/<resource>`:

| Resource | Verbs | Job |
|---|---|---|
| `smartlicenses` | GETALL/POST | View/register Smart Licensing status for FMC |
| `devicelicenses` | GETALL/PUT | View/assign feature licenses (e.g., Threat, Malware, URL Filtering) per device |

**Search** — root `/fmc_config/v1/domain/{domainUUID}/search/<resource>`:

| Resource | Verbs | Job |
|---|---|---|
| `global` | GETALL | Global search across FMC (objects, policies, devices) |
| `object`, `policy`, `device` | GETALL | Scoped search within objects, policies, or devices — useful for "where is this object used" style automation |

**System Information** — root `/fmc_platform/v1/info/<resource>`:

| Resource | Verbs | Job |
|---|---|---|
| `domain` | GET/GETALL | Enumerate domains (useful in multidomain deployments to get each Domain UUID) |
| `serverversion` | GET/GETALL | FMC software version/build info via API (API equivalent of `show version`) |

**Update Packages** — root `/fmc_config/v1/domain/{domainUUID}/updates/<resource>`:

| Resource | Verbs | Job |
|---|---|---|
| `upgradepackages` | GET/GETALL/POST/DELETE | Manage upgrade package files staged on FMC |
| `upgrades` | POST | **Kick off an upgrade** on target device(s) via API |
| `cancelupgrades`, `retryupgrades`, `revertupgrades` | POST | Cancel an in-progress upgrade, retry a failed one, or revert a completed one |
| `applicabledevices` | GETALL | Which devices are eligible for a given upgrade package |

**Policy Assignment Services** — root
`/fmc_config/v1/domain/{domainUUID}/assignment/policyassignments`:

| Resource | Verbs | Job |
|---|---|---|
| `policyassignments` | GET/GETALL/POST/PUT | Assign a policy (ACP, NAT, platform settings, etc.) to one or more devices — the API way to do what the GUI's policy "Deploy to" / target-device picker does |

**Status Services**:

| Resource | Verbs | Job |
|---|---|---|
| `job/taskstatuses` | GET/GETALL | Generic long-running task status polling, used across many POST operations that return an async job |

---

## Practical notes shared across all categories

- **Rate limits (fixed, not configurable):** up to 300 GET requests/minute per source IP; only
  **one** non-GET (PUT/POST/DELETE) request at a time per device; max 10 concurrent
  connections per IP. Exceeding any of these returns HTTP 429.
- **Payload limit:** 2,048,000 bytes per request (both raw API and API Explorer). Larger
  payloads return HTTP 422.
- **Bulk operations** exist for: access rules (`?bulk=true`, up to 1000 rules/call), object
  overrides, and some DELETE operations (`bulk=true` + `filter=...`) — check each resource's
  table above/the API Explorer before assuming bulk support.
- **Object Overrides:** almost any object under Object Services can have a **per-device or
  per-domain override value** via the `overrides` sub-resource — useful for shared objects
  (e.g., a "Branch-LAN" network object) that needs a different actual value at different
  sites without maintaining separate objects.
- **`GETALL` pagination:** 25 results per page by default, raise with `limit` up to 1000; use
  `offset` to page through more.
- Full, always-current, click-through documentation of every field per resource:
  `https://<fmc-ip>/api/api-explorer` — this catalog tells you *what exists and its job*;
  the Explorer tells you the exact JSON schema to POST/PUT.
