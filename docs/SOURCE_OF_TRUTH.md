# Release 2 Source of Truth

## Active development root

`D:\projects\MNE_Brain_v2` is the only active Release 2 implementation root. New Release 2 code, contracts, tests, and documentation belong here.

## Release boundaries

| Location | Role | Change policy |
|---|---|---|
| `D:\projects\MNE_Brain_v1` | Release 1 reference baseline | No feature work; preserve for comparison |
| `D:\projects\MNE_Brain_v2` | Release 2 active development | All new implementation work |
| `D:\projects\MNE_Brain\release-2\docs` | Historical Release 2 documentation copy | Do not treat as executable source |
| `D:\projects\MNE_Brain\MNE_Brain` | Earlier Release 1-style implementation | Do not modify as part of Release 2 work |

## Canonical content rules

- Permanent infrastructure facts belong in `knowledge/`.
- Transient telemetry, incident artifacts, and audit output belong in `operations/` and are local-only unless deliberately sanitized and promoted.
- Reusable troubleshooting experience belongs in `intelligence/`.
- Tests use sanitized fixtures under `tests/`; they must not depend on operational artifacts.
- Profiles, schemas, tasks, and approved action templates define the contracts used by the core implementation.
- P10 prepared plans, approvals, results, and audit records exist in memory only. They must not be written to `operations/`, canonical knowledge, browser storage, or tracked files.
- P11 threads, turns, messages, events, external authorizations, tool approvals, and workspace plans are in memory by default. Provider profiles contain credential-reference names only; conversation content never becomes canonical knowledge automatically.

## Change entry points

1. Update the relevant contract or ADR before changing a cross-cutting behaviour.
2. Keep live-device work out of the baseline and behind the approved verification policy.
3. Add an isolated test before claiming a behaviour is verified.
4. Promote stable facts from `operations/` to `knowledge/` only through a reviewed evidence-backed process.
5. Treat `config/p10_operation_catalog.yaml`, `config/p10_action_policy.yaml`, ADR-017, and the nine P10 schemas as the write-execution source of truth; the GUI contains no command or risk logic.
6. Treat ADR-018, the ten P11 schemas, `config/provider_catalog.yaml`, `config/p11_security_policy.yaml`, and `config/p11_tool_policy.yaml` as the conversation/provider/tool source of truth. Infrastructure writes remain impossible outside P10.
