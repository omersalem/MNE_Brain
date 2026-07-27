# Phase D.5 — Investigation Planning Engine Specification

## Purpose
The Investigation Planning Engine runs after the Query Router (Phase D) and Evidence Pack Builder (Phase C). Before any live verification or diagnostic troubleshooting occurs, the Brain builds a structured Investigation Plan.

## Core Rules & Intelligence Principles
1. **Reasoning Only:** The Investigation Planning Engine performs AI reasoning ONLY. It NEVER executes commands directly.
2. **Highest Information Gain Analysis:** Evaluates candidate checks and selects the single check/query yielding maximum diagnostic clarity.
3. **Stop Early Principle:** Defines explicit stop conditions and confidence thresholds. If Knowledge Base evidence is sufficient, live verification is marked unnecessary.
4. **Evidence Ranking:** Prefers one high-value observation over multiple low-value observations.
5. **Observation vs Interpretation Separation:** Maintains strict boundaries between raw observed facts and AI diagnostic hypotheses.
6. **Binary Investigation Strategy:** Structures checks to halve the search space at each diagnostic step.
7. **Operational Cost Minimization:** Minimizes operational cost, total live commands, and device access requests.
