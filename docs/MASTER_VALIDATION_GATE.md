# Master Validation Gate

`python -B scripts/validate_brain.py` runs 22 deterministic offline gates. Gate 21 verifies P10. Gate 22 verifies the P11 provider catalog, local thread lifecycle, disabled global P7/P10 execution, and exact eleven-module GUI inventory including owner authentication and the operational activity stream.

The master gate is non-connecting and cannot establish production readiness. P10/P11 focused tests and offline pilots remain separate required CI steps.
