# P7 Live Validation Report

**Date:** 2026-08-16  
**Authorization:** explicit sole-owner `proceed`  
**Scope:** all 46 canonical entities, read-only transport validation  
**Retention:** none; this document records aggregate outcomes only

## Outcome

| Result | Entities |
|---|---:|
| Canonical target reachable, unauthenticated, trust 0 | 17 |
| Documented candidate reachable, identity proof required, trust 0 | 17 |
| Target unreachable on governed management port | 9 |
| SNMPv3 identity and credential not configured | 3 |
| Total | 46 |

## Permanent credentialed baseline — 2026-08-18

The owner supplied corrected credentials, approved the current observed identities for local pin enrollment, and excluded the Ramallah Gold switch from scope. The original baseline covered 28 schema-governed bindings. The current catalog has 32 bindings: 31 active and one owner-excluded.

| Binding result | Count |
|---|---:|
| Original active bindings returning authenticated transport success | 27 |
| Current targeted additions returning accepted evidence (Exchange PowerShell and corrected Fujitsu SW1) | 2 |
| Current targeted additions blocked (DC2 WinRM, vCenter inventory authorization, FMC REST access) | 3 |
| Owner-excluded bindings | 1 |

Twenty-five active SSH bindings use locally stored host-key pins, four use exact Kerberos FQDNs, and two use pinned TLS certificates. The former `p7-san` target is now correctly modeled as Fujitsu SW1. Its earlier prompt-only behavior was caused by an extra interactive exit; the corrected session returned meaningful version evidence. It is not treated as the SAN controller. All identity and credential values remain in the ignored credential environment file.

The pinned FortiGate edge separately completed one authenticated `system_status` read and produced fresh trust-5 evidence in memory. No raw device output, credential, incident record, or audit record was persisted.

HTTPS checks against the reachable internal web and management endpoints failed closed at certificate validation because their chains are not trusted by the local runtime. P7 did not disable certificate verification. SSH endpoints without configured host-key pins were not authenticated. Windows HTTP WinRM was not used with a TrustedHosts change. SNMP was not downgraded to a shared community string.

## Still disabled or blocked

- every live transport is disabled at rest;
- canonical knowledge promotion and target rewriting;
- first-use SSH/TLS trust;
- automatic remediation, notification, ticketing, paging, and assignment;
- persistent incident, audit, raw response, or evidence storage;
- automatic authenticated reads without a fresh explicit owner `proceed` instruction;
- SNMP until SNMPv3 engine identity, credentials, and dependency are configured;
- DC2 Windows remoting until WinRM is reachable; Exchange PowerShell is validated.
- vCenter/FMC object collection until the configured accounts receive the required read-only API access.
- Veeam access from this workstation, the actual SAN controller binding, and a separate Fujitsu SW2 identity pin.
