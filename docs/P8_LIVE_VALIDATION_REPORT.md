# P8 Live Validation Report

## Result

- Date: 2026-08-18
- Owner instruction: explicit `proceed` for all P8
- Scenario families: 8/8 passed
- Exact read-only collection attempts: 13/13 succeeded
- Unique operational bindings exercised: 10
- Evidence handoffs: 8/8 accepted while fresh, then discarded
- Raw output retained: no
- Credentials returned: no
- Incidents or audits persisted: no
- Notifications, tickets, pages, or assignments: none
- Remediation attempts: none
- Policy after every scope: disabled

The original validation covered Nablus branch firewall, edge VPN firewall, F5 publishing, AD/DNS, Exchange, vCenter, the then-ambiguous storage-side endpoint, FTD, FMC, and the core switch. P9 later corrected that endpoint to Fujitsu SW1 and added dedicated DC2, Exchange PowerShell, vCenter REST, and FMC REST bindings. Repeated dependency checks use the same exact bindings.

## Interpretation

The result demonstrates authenticated access to each selected management endpoint and successful ingestion of compact attributable evidence. It does not prove end-user service health or establish any root cause. No canonical target was automatically changed: the SAN endpoint remains `AMBIGUOUS_DO_NOT_PROMOTE`, while address mismatches remain owner-review candidates.

Validation was owner-controlled, exact-scope, read-only, and in memory. The repository policy remained disabled at rest before and after every scope.
