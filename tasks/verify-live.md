# Task: Live Read-Only Verification (`tasks/verify-live.md`)

> **Phase F Requirement:** Live verification operations MUST execute only allowed read-only commands via registered platform adapters (`scripts/adapters/`). Raw telemetry is saved under `operations/evidence/` and normalized evidence is returned.

## Verification Workflow
1. Receive Investigation Plan (Phase D.5) specifying target device and `check_id`.
2. Check `config/action_policy.yaml` to confirm `check_id` is Level 0 (Read Only) and explicitly permitted for the device profile.
3. Obtain credentials by secret reference (`secret_ref`).
4. Invoke `scripts/live_verify.py --device <id> --check <check_id>`.
5. Normalize raw telemetry into timestamped live evidence (`operations/evidence/live-<id>-<check>-<timestamp>.json`).
