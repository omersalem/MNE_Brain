# Action Template Governance

Files under `actions/approved/` are legacy candidates; the directory name does
not grant execution readiness. The authoritative field is `template_status`.

## Statuses

- `unreviewed`: cannot advance to execution readiness.
- `approved`: means reviewed only by `MNE-BRAIN-OWNER` and must include a template version, last-review date,
  non-empty pre/post checks, and a non-placeholder rollback for every change.
- `retired`: retained for history and cannot advance.

## Safety boundary

The remediation engine produces fingerprints and checklists, not raw commands.
It never invokes a driver. A plan marked `READY_FOR_SEPARATE_EXECUTION_GATE`
still requires a deliberately enabled bridge joining policy, execution, transport,
exact target scope, and an explicit owner instruction. Audit remains in memory and retention is `NONE` unless the owner explicitly requests persistence.

All current legacy templates are intentionally marked `unreviewed` pending that
review. Level 4 actions remain prohibited regardless of template status.
