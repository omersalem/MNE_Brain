# P10 Local API

All endpoints are under `/api/p10`, are in-memory-only, and reject non-loopback clients. `OWNER_FULL_CONTROL` mutation endpoints require the owner cookie, same-origin `X-P10-CSRF`, and a one-time `request_nonce`.

## Read endpoints

- `GET /session` — local CSRF token and disabled-at-rest state.
- `GET /operations` — redacted catalog metadata.
- `GET /readiness` — non-secret per-platform and per-binding status, credential-reference names, renderer coverage, and exact blockers.
- `GET /plans/{plan_id}` — redacted in-memory prepared plan.
- `GET /results/{execution_id}` — redacted in-memory result.

## Mutation endpoints

- `POST /plans/prepare`
- `POST /plans/prepare-critical`
- `POST /plans/{plan_id}/approve`
- `POST /plans/{plan_id}/execute`
- `POST /plans/{plan_id}/cancel`
- `POST /plans/{plan_id}/rollback/prepare`

The core—not the GUI—validates fields, parameters, evidence, target, binding, protocol, identity, risk, full-plan digest, owner-session binding, expiry, replay, execution state, and rollback. The original approval covers the displayed prechecks, change, postchecks, and only the displayed rollback on a declared failure condition. The rollback endpoint returns that contract and never opens a second approval. Execution is disabled in the shipped API context. Every binding is independently blocked until a separate write credential and a read-only privilege probe establish write authorization.
