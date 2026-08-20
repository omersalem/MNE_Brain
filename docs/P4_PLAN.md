# P4 Incident Operations Plan

## Objective

P4 turns a validated owner report and P3 investigation into a professional, portable incident case without depending on a ticketing platform. It captures affected service, target, branch/user scope, and availability; calculates a provisional priority; applies `MNE-BRAIN-OWNER`; and produces bounded evidence objectives and a compact handoff packet.

P4 does not verify reported impact, confirm priority, establish an SLA, notify a team, persist incident data, connect to infrastructure, call an external AI, or execute remediation.

## Implemented workstreams

| Workstream | Implementation |
|---|---|
| P4A incident intake | Dedicated JSON schema, backend service, REST endpoint, and presentation-only form for target, symptom, service, scope, availability, and branch/user impact |
| P4B priority | `UNASSESSED` or `PROVISIONAL_P1` through `PROVISIONAL_P4`, based only on operator-reported impact |
| P4C ownership | One fixed project owner, `MNE-BRAIN-OWNER`; no department routing or notification |
| P4D continuation | Schema-valid prior-case continuation with exact question and target matching |
| P4E objective tracking | Reported collected/skipped objectives are suppressed; reported failures remain pending and require retry review |
| P4F timeline | Maximum 20 system-recorded or operator-reported events with explicit truth state |
| P4G handoff | Maximum 8,000-character packet excluding IP addresses, commands, raw output, credentials, and invented SLAs |
| P4H readiness gate | Evidence objectives are withheld until the target resolves exactly and impact is assessed |
| P4I workflow governance | Minimal sole-owner status for explicit authorization, in-memory audit, no retention, and disabled automation |

## Provisional priority boundary

Priority is a triage suggestion, not a declaration of verified impact:

- P1 covers reported security/data-loss impact, ministry-wide impact, or an unavailable multi-branch service.
- P2 covers a reported unavailable branch, public service, or multi-user service, and degraded multi-branch impact.
- P3 covers reported degraded multi-user or branch impact and unavailable single-user impact.
- P4 covers remaining bounded reported impact.
- Missing scope and availability remains `UNASSESSED`.

Every provisional priority requires owner confirmation. No response time is attached because the owner has not configured an SLA.

## Completion criteria

- All priority rules preserve `REPORTED_IMPACT_ONLY` and require owner confirmation.
- Unknown targets cannot release evidence objectives.
- Unknown scope/availability cannot release evidence objectives.
- Branch and user counts must agree with the selected scope.
- The project has one owner and never requests department approval or sends a notification.
- Read-only troubleshooting requires an explicit owner `proceed`.
- Configuration changes and remediation require explicit owner instructions.
- Audit remains in memory and retention remains `NONE` unless the owner explicitly requests persistence.
- Cross-target or malformed continuations fail closed.
- Check updates remain reported and never become verified evidence.
- Handoff remains within 8,000 characters and contains no sensitive transport material.
- No live access, AI call, notification, persistence, or remediation occurs.
- P4 pilot, master validation, schema validation, and classified pytest suite pass.
