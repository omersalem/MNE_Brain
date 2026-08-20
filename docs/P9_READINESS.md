# P9 Readiness

## Implemented

- Eight deep-diagnostic families and 30 immutable read-only checks.
- Exact scenario, binding, identity, command, freshness, and output-size gates.
- Platform normalizers for FortiGate, F5, Windows, Linux, vCenter REST, FMC REST, Cisco security, and switching evidence.
- Adaptive next-check selection with a four-check session budget.
- Evidence-referenced AI assessment contract and 95% stop-early gate.
- Planning-only REST API and GUI.
- Owner-gated live CLI, offline pilot, regression tests, schema, ADR, and master-gate integration.

## Truth boundary

Normalized management evidence can narrow the failing layer. It does not by itself prove end-user impact or causality. A root-cause statement belongs to the AI reasoning layer and must cite accepted live evidence.

## Known gaps

- Veeam is not reachable from this workstation and was deliberately not probed.
- The pinned vCenter REST session authenticates, but the configured account is not authorized for host or datastore inventory.
- The pinned FMC endpoint rejects REST token generation with HTTP 403; SSH access does not grant API access.
- MNE-DC2 resolves and answers Kerberos/LDAP, but WinRM HTTP and HTTPS are unreachable from this workstation.
- The actual SAN controller is not mapped to a trusted transport binding.
- Fujitsu SW1 is now correctly identified and live-validated; Fujitsu SW2 has no separately trusted host-key binding.

These gaps remain explicit unknowns; no substitute evidence is relabeled as proof.

## Live acceptance

All eight families and the current 30-check catalog were exercised across owner-authorized read-only sessions on 2026-08-18. Twenty-four checks produced accepted normalized evidence. Branch, VPN, web publishing, and Exchange have complete current check sets; DNS/AD, VMware, FMC/FTD, and storage/core remain partial for the blockers above. Policy returned to disabled after every session.
