# ADR-014: P7 Owner-Gated Live Transports

## Status

Accepted for Release 2 on 2026-08-16.

## Decision

P7 implements minimal SSH, HTTPS REST, PowerShell/WinRM, VMware REST, SNMP-readiness, and TCP preflight boundaries for all 46 canonical entities. Every transport is disabled at rest and requires the sole owner to say `proceed` for an exact read-only entity/check scope.

Permanent local bindings are schema-governed separately from canonical knowledge. Twenty-seven bindings are active and one binding—the Ramallah Gold switch—is excluded by explicit owner instruction. SSH host-key and TLS certificate pins remain only in the ignored credential environment file; AD and Exchange use exact Kerberos FQDNs.

Authenticated evidence is accepted only when the connection identity is proven by a configured SSH host-key pin, verified TLS chain or certificate pin, Kerberos/WinRM HTTPS identity, or SNMPv3 engine identity. Reachability alone remains trust 0. A documented target that conflicts with canonical identity is a candidate only and can never silently rewrite canonical knowledge.

Credentials remain in ignored local environment files and are resolved only inside the transport. P7 returns no credentials or raw transport errors. Audit and evidence are in memory only with no retention, notification, ticket, page, assignment, remediation, or automatic canonical promotion.
