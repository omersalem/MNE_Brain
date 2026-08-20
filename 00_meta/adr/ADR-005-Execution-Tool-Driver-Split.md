# ADR-005: Separation of Execution Engine from Tool Drivers

> **Status:** APPROVED  
> **Date:** August 1, 2026  
> **Decision Makers:** Lead Software Architect & Chief AI Systems Architect  

---

## Context
When protocol tools (SSH, REST, PowerShell, WinRM) contain embedded retry, timeout, audit, and rollback logic, code becomes duplicated, brittle, and difficult to test across vendors.

## Decision
We decided to separate execution orchestration from protocol drivers:
* **Execution Engine (`core/execution/`):** Handles retry policies, timeout handling, parallel execution, task cancellation, audit logging, progress tracking, and rollback orchestration.
* **Tool Engine Drivers (`core/tools/drivers/`):** Low-level protocol drivers (SSH, REST, PowerShell, WinRM, VMware, SQL, SNMP) containing **zero orchestration logic**.

## Consequences
* **Positive:** Protocol drivers are lightweight, clean, and easily unit-tested.
* **Positive:** Centralized retry, logging, and rollback handling.
* **Positive:** Easily extensible to new infrastructure protocols.
