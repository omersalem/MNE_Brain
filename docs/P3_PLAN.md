# P3 Offline Troubleshooting Intelligence Plan

## Objective

P3 makes offline incident handling consistent and fast across Ministry infrastructure domains. It coordinates routing, exact entity resolution, declared adjacency, evidence validation, bounded next-check selection, reasoning state, and a compact AI handoff.

P3 does not activate live access, call an external AI provider, persist incident data, promote knowledge, or execute remediation. It may consume a small, fresh P2 evidence envelope when explicitly allowed by P3 policy.

## Implemented workstreams

| Workstream | Implementation |
|---|---|
| P3A incident contract | Schema-valid investigation result with explicit status, metrics, safety, evidence, and clarification fields |
| P3B exact scope | Target-dependent requests require exactly one canonical entity; unknown and ambiguous targets request clarification |
| P3C adjacency context | One bounded set of forward and reverse declared relationships; every related entity remains operationally `UNKNOWN` |
| P3D evidence objectives | Category and service-aware read-only evidence objectives selected from policy, without commands |
| P3E AI handoff | Maximum 6,000-character structured context containing accepted evidence, unknowns, adjacency, and reasoning constraints |
| P3F API integration | Chat API delegates to the orchestrator and no longer guesses a platform or creates synthetic drift input |
| P3G observability | Redacted in-memory tracing by default; persistence requires explicit opt-in |

## Deterministic incident flow

1. Validate and bound the question.
2. Classify the request before retrieval.
3. Resolve exactly one canonical entity or request clarification.
4. Load bounded declared adjacency as context only.
5. Accept evidence only through the evidence-pack validator and current phase policy.
6. Evaluate whether evidence supports, conflicts, or remains insufficient.
7. Select up to five read-only evidence objectives; do not generate or expose commands.
8. Build a compact AI handoff that forbids unsupported health, causality, root-cause, and remediation claims.
9. Return metrics and explicit non-execution flags.

## Completion criteria

- All seven representative Ministry domains resolve deterministically.
- Unknown targets never produce inferred assets or checks.
- Documentation and declared relationships never become current-state evidence.
- Forged or injected live evidence is rejected while offline policy is active.
- Evidence stays within 1,500 estimated tokens and AI handoff within 6,000 characters.
- No live connections, external AI calls, persistence, lifecycle promotion, or remediation occurs.
- P3 pilot, master gate, schema validation, and classified pytest suite pass.

## Future activation boundary

Simplified P0 Git containment is complete. The first reviewed P2 evidence intake was completed on 2026-08-16 with two FortiGate checks. Further live collection still requires a fresh P2 authorization window; P3 cannot initiate transport and its existing intake allowlist cannot be expanded implicitly.
