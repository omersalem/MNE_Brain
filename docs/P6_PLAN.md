# P6 Multi-Platform Connector Plan

## Objective

P6 completes deterministic read-only connector planning for every canonical Ministry entity while keeping Python minimal and all diagnosis in the runbook/AI layer.

## Completed scope

| Workstream | Result |
|---|---|
| Connector contract | Schema fixes sole owner, exact targeting, read-only checks, technical review sources, and disabled side effects |
| Catalog | 15 connector families covering 46/46 entities exactly once |
| Planning | Redacted plans expose check IDs, evidence objectives, and operation fingerprints only |
| Adapter boundary | All families reuse the injected evidence adapter for budgets, redaction, provenance, and trust |
| Offline validation | Every entity passes fixture routing; all fixture evidence remains simulated trust 0 |
| Live gate | Repository live policy is disabled; exact owner-controlled activation remains mandatory |
| Presentation | Read-only API, dashboard metrics, and GUI connector readiness view |

## Platform sequence completed

FortiGate edge and fleet, Cisco switching, Cisco FMC, Cisco FTD, F5 BIG-IP/WAF, Windows AD/DNS, Exchange, VMware vCenter, VMware ESXi, storage arrays, Veeam, published web applications, Linux/application hosts, and network printers.

## Boundary

P6 offline readiness means exact routing, allowlists, redaction, and normalization were validated without a network connection. It does not prove credentials, endpoint identity, API compatibility, live reachability, device health, or production readiness. Every future live read remains one exact owner-authorized scope.
