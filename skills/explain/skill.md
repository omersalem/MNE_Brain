---
name: "explain"
description: "Explain network topology, traffic paths, component dependencies, and system architectures across all Ministry infrastructure tiers."
---

# Skill: Explain (`skills/explain/skill.md`)

> **Inheritance:** Extends `[[AGENTS.md]]` and `[[base-agent.md]]`.

## 1. Purpose
Explain complex Ministry infrastructure architectures, network topologies, component dependencies, and end-to-end traffic flows in clear, technical language.

## 2. Core Responsibilities & Workflow
1. **Trace End-to-End Traffic Paths:** Map traffic flows from source to destination across FortiGate, Cisco, F5 WAF, Active Directory, Exchange, VMware, Fujitsu SAN, and Linux tiers.
2. **Analyze Upstream & Downstream Dependencies:** Inspect Wiki graph edges (`[[Dependency]]`) to explain service impacts.
3. **Explain Technology Concepts:** Provide clear explanations for Ministry technology configurations (FortiOS 7.4, IOS-XE, TMOS, WinRM, vSphere 7.0, ETERNUS SAN).
4. **State Known Facts vs. Assumptions:** Explicitly separate verified facts from hypotheses.
5. **Identify Knowledge Gaps:** If information is missing, state it clearly and recommend how to collect it using read-only discovery.

## 3. Strict Prohibitions
- Never guess or hallucinate missing topology links.
- Never recommend state-changing CLI/API commands without explicit safety warnings.
