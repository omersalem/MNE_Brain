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

## Change entry points

1. Update the relevant contract or ADR before changing a cross-cutting behaviour.
2. Keep live-device work out of the baseline and behind the approved verification policy.
3. Add an isolated test before claiming a behaviour is verified.
4. Promote stable facts from `operations/` to `knowledge/` only through a reviewed evidence-backed process.
