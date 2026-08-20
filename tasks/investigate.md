# Task Specification: Infrastructure Investigation Engine

> **Task ID:** `investigate`  
> **Title:** Stateful Incident Investigation & Root Cause Diagnostics  
> **Path:** `tasks/investigate.md`  

---

## 🎯 Task Objective
Perform systematic, stateful incident diagnosis across enterprise infrastructure using empirical telemetry, Information Gain ($H$) evaluation, and the **Stop Early Principle**.

---

## 🔄 Stateful Diagnostic Loop

1. **Formulate Hypotheses:** Generate initial candidate root causes with baseline prior probabilities.
2. **Calculate Information Gain ($H$):** Prioritize diagnostic actions that yield maximum information gain.
3. **Evaluate Telemetry Need:** Produce a bounded evidence objective. Do not execute it unless the separate P2 policy and activation gates authorize the exact target and check.
4. **Evaluate Certainty:** Update hypothesis confidence scores.
5. **Stop Early Check:** If attributable live evidence supports a hypothesis above the configured threshold, return only an evidence-scoped conclusion. Otherwise retain unknowns and request the next approved check.

## P3 orchestration boundary

- Require exactly one canonical target for target-dependent troubleshooting.
- Treat `related_entities` as documented adjacency, never current health or causality.
- Use at most five policy-declared evidence objectives and expose no commands.
- Keep the AI handoff under 6,000 characters and the evidence pack under 1,500 estimated tokens.
- While `config/p3_troubleshooting_policy.yaml` disables live input, reject every supplied verification result.
- Never run lifecycle promotion or remediation from the incident-intake path.

---

## 📋 Task Contract Parameters

```yaml
task_id: investigate
title: Infrastructure Incident Investigation Engine
objective: Empirical root cause diagnosis using Information Gain and Stop Early logic
target_profiles:
  - profiles/fortigate.yaml
  - profiles/cisco.yaml
  - profiles/vmware.yaml
information_gain_threshold: 0.5
exit_conditions:
  - root_cause_certainty_exceeds_95_percent
  - maximum_telemetry_reads_exceeded
  - emergency_risk_blocked
```
