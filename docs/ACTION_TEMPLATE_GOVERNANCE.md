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
review. P10 supersedes the universal Level 4 prohibition: Level 4 is `CRITICAL_EXCEPTION_ONLY` and can never use the normal cataloged approval phrase or the legacy Boolean remediation path. It requires the exact critical or irreversible P10 phrase, complete warning, break-glass checks, one exact target, and a separately authorized live plan.

P10 templates live in `config/p10_operation_catalog.yaml` and conform to `p10-operation-catalog.schema.json`. Directory placement is not approval. Runtime parameters conform to each template's strict embedded schema, unknown fields are rejected, and the core renders an exact structured transaction without general shell interpolation.
