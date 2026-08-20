# ADR-016: P9 Deep Diagnostics and Evidence-Bounded Reasoning

## Status

Accepted by `MNE-BRAIN-OWNER` for P9 implementation.

## Decision

P9 extends P8 management-access baselines with platform-specific read-only diagnostics. Every check is a schema-governed immutable operation attached to one exact P7 binding. One session may address at most three bindings and four checks. Operations never enter the public API, GUI, or AI handoff.

Raw output exists only inside a collector long enough to produce compact normalized observations and a hash prefix. It is then discarded. Only fresh attributable trust-level-5 evidence may enter reasoning.

Python validates scope, collects, normalizes, ranks checks by information gain, and enforces evidence references. It does not encode root-cause conclusions. An optional injected AI assessment must cite accepted evidence. Stop early is permitted only when the assessment provides a root cause, references accepted evidence, and reaches confidence `0.95` or higher.

## Governance

- sole owner: `MNE-BRAIN-OWNER`
- explicit owner `proceed` for live reads
- in-memory audit and evidence only
- no retention
- disabled at rest and after every session
- no automatic diagnosis, remediation, persistence, canonical promotion, notification, ticket, page, or assignment

## Known limitation

Direct Veeam job-history diagnostics are not represented as live evidence until an exact Veeam credential and identity binding is configured. The current storage-side binding also lacks a validated identity or health command and remains ambiguous. P9 reports these gaps and does not infer backup or SAN health from vCenter or management reachability.
