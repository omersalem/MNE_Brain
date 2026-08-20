# MNE_Brain Release 2 (v2)

> **Status:** P9 deep read-only diagnostics and evidence-bounded reasoning are implemented over the P7/P8 layers. Live policy and production readiness remain disabled at rest.

Release 2 is the independent implementation line for an evidence-driven Ministry infrastructure investigation platform. Release 1 remains a separate reference baseline and is not modified by this project.

The intended pipeline is:

```
Question or alert -> entity resolution -> focused evidence -> AI investigation plan
-> bounded read-only verification -> evidence-based answer -> controlled remediation
```

The GUI is presentation-only. Deterministic code enforces scope, policy, evidence handling, and safety boundaries; AI reasoning develops hypotheses and investigation plans.

See [the development baseline](docs/DEVELOPMENT_BASELINE.md) and [current Release 2 status](docs/RELEASE_2_STATUS.md) before running the project.

P7 implements SSH, REST, PowerShell/WinRM, VMware, SNMP-readiness, and bounded TCP preflight behind exact-target and identity gates. It enables no remediation, notification, ticket, page, assignment, or persistent audit/evidence storage. See [P7 live validation](docs/P7_LIVE_VALIDATION_REPORT.md) and [P7 readiness](docs/P7_READINESS.md).

P8 adds eight exact-scope troubleshooting scenarios, safe reconciliation for all 32 operational bindings, fresh trust-5 evidence intake, a compact root-cause reasoning handoff, and a planning-only GUI/API. The planner never connects; the local live pilot requires explicit owner `proceed` and retains no raw output. See [P8 plan](docs/P8_PLAN.md), [P8 readiness](docs/P8_READINESS.md), and [P8 live validation](docs/P8_LIVE_VALIDATION_REPORT.md).

P9 adds 30 platform-specific deep checks, ephemeral output normalization, adaptive information-gain ordering, evidence-referenced AI assessments, and a 95% stop-early gate. Python does not diagnose. Veeam remains unreachable from this workstation; vCenter inventory authorization, FMC API access, DC2 WinRM, the actual SAN controller, and Fujitsu SW2 identity remain explicit gaps. See [P9 plan](docs/P9_PLAN.md), [P9 readiness](docs/P9_READINESS.md), and [P9 live validation](docs/P9_LIVE_VALIDATION_REPORT.md).

The reusable authenticated baseline is `python scripts/run_p7_authenticated_baseline.py --owner-proceed`. It executes only the 31 active schema-governed bindings, skips the owner-excluded Ramallah Gold switch, summarizes results without raw output, and leaves live policy disabled at rest.

## Local development setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Offline quality gate

```powershell
python scripts/validate_schemas.py
python scripts/validate_p0_containment.py
python scripts/validate_brain.py
python scripts/run_benchmarks.py
python scripts/run_p6_offline_pilot.py
python scripts/run_p8_offline_pilot.py
python scripts/run_p9_offline_pilot.py
$env:PYTHONDONTWRITEBYTECODE='1'
python -B -m pytest -q -p no:cacheprovider -m "offline or integration"
```

The complete current test collection is classified and safe to run offline. It uses disposable fixtures for recovery, failure, and scalability scenarios. Passing it does not demonstrate live service health, credential safety, or production readiness.

## P2 boundary

P2 adds fail-closed read-only adapter contracts, attributable live-evidence normalization, offline operational pilots, and operator runbooks. Simplified P0 Git containment is complete: local `.env` files may contain secrets and remain ignored. The first exact-target FortiGate pilot succeeded through the pinned adapter, and repository live policy was disabled immediately afterward. See [the P0 containment policy](docs/P0_SIMPLE_CONTAINMENT.md), [the P2 pilot result](docs/P2_FIRST_LIVE_READ_REPORT.md), [the P2 plan](docs/P2_PLAN.md), and [P2 readiness](docs/P2_READINESS.md).

Run the non-connecting live-pilot readiness check with `python -B scripts/preflight_p2_live_pilot.py`. A blocked exit is expected until the exact target, local credential reference, fixed owner authorization, and live policy are deliberately configured.

## P3 boundary

P3 coordinates exact-target routing, bounded declared adjacency, evidence validation, read-only evidence objectives, reasoning state, and a compact AI handoff across Ministry domains. It makes no live connection. Its policy accepts at most two fresh, scoped P2 FortiGate evidence records through the governed in-memory provenance envelope; it rejects stale, simulated, wrong-target, or malformed input. See [the P3 plan](docs/P3_PLAN.md), [P3 readiness](docs/P3_READINESS.md), [the offline pilot report](docs/P3_OFFLINE_PILOT_REPORT.md), and [the first P3/P4 live-evidence session](docs/P3_P4_LIVE_EVIDENCE_SESSION_REPORT.md).

## P4 boundary

P4 adds a schema-validated incident-intake form and `/api/incidents/intake` endpoint, provisional priority, sole-owner control, safe case continuation, evidence-objective gating, and a bounded handoff packet. A read-only governance endpoint exposes `OWNER_CONTROLLED`, `MNE-BRAIN-OWNER`, in-memory audit, no retention, and disabled automation. Read-only troubleshooting requires the owner's explicit `proceed`; changes and remediation require explicit owner instructions. P4 does not verify impact, invent an SLA, notify, ticket, page, auto-assign, auto-remediate, or persist case data. See [the P4 plan](docs/P4_PLAN.md), [P4 readiness](docs/P4_READINESS.md), [the original offline pilot](docs/P4_OFFLINE_PILOT_REPORT.md), [the professional intake report](docs/P4_INCIDENT_INTAKE_REPORT.md), and [the sole-owner governance report](docs/P4_WORKFLOW_GOVERNANCE_REPORT.md).

## P5 boundary

P5 adds 12 schema-governed troubleshooting runbooks, deterministic metadata-only selection, a dedicated Cisco FMC/FTD path, 46/46 context and owner-reviewed procedure coverage, P4 handoff guidance, a read-only API, and a GUI readiness view. Review means the procedure is suitable for bounded troubleshooting; it does not verify current health or authorize collection. See [the P5 plan](docs/P5_PLAN.md), [P5 readiness](docs/P5_READINESS.md), [the review report](docs/P5_OPERATIONAL_REVIEW_REPORT.md), and [the P5 pilot report](docs/P5_OFFLINE_PILOT_REPORT.md).

## P6 boundary

P6 adds 15 schema-governed read-only connector families covering 46/46 canonical entities across FortiGate, Cisco switching/FMC/FTD, F5, Windows AD/DNS, Exchange, VMware, storage, Veeam, web/Linux applications, and printers. Plans contain fingerprints rather than raw operations, and every entity passes trust-0 injected transport validation. Only the FortiGate edge has an implemented owner-gated live transport; repository live policy remains disabled for every platform. See [the P6 plan](docs/P6_PLAN.md), [P6 readiness](docs/P6_READINESS.md), and [the P6 pilot report](docs/P6_OFFLINE_PILOT_REPORT.md).

## Local development server

```powershell
python core/api/server.py
```

Use only with non-production configuration. The development server does not authorize live verification or remediation.
