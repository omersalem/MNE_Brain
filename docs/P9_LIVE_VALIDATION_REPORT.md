# P9 Live Validation Report

Live acceptance results are recorded only as aggregate normalized capability evidence. Raw output, credentials, incident state, and audit records are not retained.

The policy is owner-controlled, exact-scope, read-only, in memory, and disabled after every session.

## Acceptance result

- Date: 2026-08-18
- Scenario families executed: 8/8
- Exact current read-only checks attempted across owner-authorized sessions: 30/30
- Normalized evidence records accepted: 24/30
- Families with complete current evidence sets: 4/8
- Families with truthful partial evidence: 4/8
- Raw output, credentials, persistence, external AI, remediation, notification, ticketing, paging, assignment, and canonical promotion: 0

| Family | Result | Accepted | Normalized live signals |
|---|---:|---:|---|
| Branch WAN | `READY_FOR_AI_REASONING` | 3/3 | Physical interfaces, routes/default route, and IPsec tunnel summary collected from Nablus. |
| SSL-VPN | `READY_FOR_AI_REASONING` | 3/3 | Session, SSL-VPN configuration, and routing evidence collected from the central FortiGate. |
| Web publishing | `READY_FOR_AI_REASONING` | 4/4 | F5 virtual/pool aggregates plus backend service and listening-port evidence collected. Aggregate offline/unknown labels require an exact application VIP and pool before interpretation. |
| DNS/AD | `PARTIAL_EVIDENCE_COLLECTION_FAILED` | 3/4 | DC1 services, replication summary, and local resolution succeeded. DC2 resolves and answers Kerberos/LDAP, but neither WinRM port is reachable. |
| Exchange | `READY_FOR_AI_REASONING` | 4/4 | Existing service/error/AD checks remain accepted. Dedicated Exchange PowerShell additionally reported one DAG, 12 healthy or mounted copies, zero failed copies, one queue, and zero queued messages. |
| VMware | `PARTIAL_EVIDENCE_COLLECTION_FAILED` | 2/4 | vCenter appliance system and storage health were green. REST authentication succeeds, but host and datastore inventory are authorization-blocked. |
| FMC/FTD security | `PARTIAL_EVIDENCE_COLLECTION_FAILED` | 2/4 | FTD network and manager relationship evidence is accepted. FMC REST token generation is denied with HTTP 403, so device/deployment and interface detail remain unavailable. |
| Storage/core switching | `PARTIAL_EVIDENCE_COLLECTION_FAILED` | 3/4 | Fujitsu SW1 now returns pinned version evidence, and the two core-switch checks remain accepted. Supporting vCenter datastore inventory is authorization-blocked. |

## Truthful open gaps

- Veeam is unreachable from this workstation and received zero connection attempts.
- The actual SAN controller is not the Fujitsu SW1 target and remains unmapped.
- Fujitsu SW2 needs its own observed-and-owner-trusted host-key pin before use.
- vCenter host/datastore REST needs read-only inventory permission for the configured account.
- FMC needs a REST-authorized API account or API enablement; current token generation returns HTTP 403.
- DC2 needs WinRM reachability on 5985 or a separately pinned HTTPS configuration on 5986.

No P9 run asserted a root cause. No configuration, remediation, notification, ticket, page, assignment, canonical promotion, or persistent evidence/audit write was attempted.
