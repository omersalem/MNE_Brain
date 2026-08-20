# Release 2 Development Baseline

**Status:** P1-P6 implementation accepted offline, including reviewed runbooks and 46/46 multi-platform connector planning; production use and live collection remain disabled.

## Purpose

Release 2 is the active implementation target for MNE_Brain. Release 1 remains an untouched reference baseline in its separate project directory. This repository contains the Release 2 source, contracts, tests, and future migration work.

## Completed P1 boundaries

- P1 established a reproducible source layout, evidence boundaries, non-executing adapters, and an offline validation workflow.
- P6 adds 15 exact multi-platform connector families and validates all 46 entity routes through trust-0 injected fixtures.
- It does not run live infrastructure checks, perform remediation, or certify production readiness.
- Simplified P0 Git containment is complete; it intentionally does not add a vault or rotation workflow.
- Operational output and persistent credentials are local-only and must never be committed.

## Supported development environment

- Python: `>=3.11,<3.13`
- Runtime dependencies: `requirements.txt`
- Optional test runner: `python -m pip install ".[test]"`

Create a virtual environment and install runtime dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Safe offline checks

Before any live integration work, run the complete classified offline gate below. Passing results are development evidence only; they do not show that any Ministry device is healthy or reachable.

```powershell
python scripts/validate_schemas.py
python scripts/validate_brain.py
python scripts/run_benchmarks.py
python -B -m pytest -q -p no:cacheprovider -m "offline or integration"
```

Tests are classified as `offline`, `integration`, `live`, or `mutating`. The current CI command selects only `offline` and safe `integration` tests. No `live` or `mutating` test may enter the default gate.

## Version-control policy

The repository is initialized on `codex/release2-foundation`. Local `.env` and credential files are ignored, and CI validates that containment. No files are staged or committed automatically; version-control review remains a normal operator decision rather than a P0 prerequisite.

## Source and CI controls

- `docs/SOURCE_OF_TRUTH.md` defines the active Release 2 root and layer ownership.
- `.github/workflows/ci.yml` runs P0 containment, contracts, syntax compilation, the offline master gate, Ministry-domain evidence-flow benchmarks, and the classified safe test collection.
- CI does not load credentials, contact Ministry infrastructure, persist operational evidence, or execute remediation.
