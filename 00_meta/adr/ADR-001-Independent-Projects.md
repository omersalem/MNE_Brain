# ADR-001: Independent Project Root Separation (MNE_Brain_v1 vs MNE_Brain_v2)

> **Status:** APPROVED  
> **Date:** August 1, 2026  
> **Decision Makers:** Lead Software Architect & Chief AI Systems Architect  

---

## Context
MNE_Brain Release 1 (`MNE_Brain_v1`) represents a stable, frozen operational baseline. When initializing Release 2 (`MNE_Brain_v2`), we evaluated whether to place Release 1 inside Release 2 as nested subdirectories or maintain completely independent top-level project roots.

## Decision
We decided to structure **`MNE_Brain_v1` and `MNE_Brain_v2` as completely independent project roots** (`d:/projects/MNE_Brain_v1/` and `d:/projects/MNE_Brain_v2/`).

## Consequences
* **Positive:** Zero relative path resolution interference for Python imports and local `.env` loading.
* **Positive:** Independent git versioning, tags, dependencies (`requirements.txt`), and containerization.
* **Positive:** Clean AI tool context boundaries during code indexing and file viewing.
* **Positive:** Side-by-side behavioral benchmarking without workspace clutter.
* **Negative:** Requires copying shared reference notes into v2 during initial migration (handled automatically via `scripts/migrate_v1_to_v2.py`).
