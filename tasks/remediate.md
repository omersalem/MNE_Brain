# Task Specification: Controlled Remediation Planning

> **Task ID:** `remediate`  
> **Title:** Controlled Infrastructure Remediation Planning  
> **Path:** `tasks/remediate.md`

## Objective

Create a redacted, reviewable remediation plan after evidence, template, policy,
rollback, validation-check, and sole-owner instruction gates have all been evaluated.
This task does not execute commands or automatically run rollback.

## Mandatory safety questions

1. Does attributable live evidence support the root cause?
2. Is the template explicitly marked `approved` after sole-owner review?
3. Is the risk level allowed to advance under policy?
4. Is a real rollback defined for every change?
5. Are both pre-checks and post-checks present?
6. Did `MNE-BRAIN-OWNER` explicitly instruct this remediation plan?

A folder name never grants approval. Level 4 is always prohibited. Passing all
questions produces `READY_FOR_SEPARATE_EXECUTION_GATE`, not execution authority.

## Task contract

```yaml
task_id: remediate
title: Controlled Remediation Planning Task
objective: Produce a non-executing remediation plan after six safety gates
target_profiles:
  - profiles/fortigate.yaml
  - profiles/cisco.yaml
information_gain_threshold: 0.8
exit_conditions:
  - remediation_plan_blocked
  - remediation_plan_ready_for_separate_execution_gate
  - level_4_risk_hard_blocked
```
