---
name: "review"
description: "Audit vault quality, verify confidence ratings, detect outdated documentation, and evaluate SPOF risks."
---

# Skill: Review (`skills/review/skill.md`)

> **Inheritance:** Extends `[[AGENTS.md]]` and `[[base-agent.md]]`.

## 1. Purpose
Audit the quality, freshness, confidence ratings, and Single Point of Failure (SPOF) risks of the Digital Twin.

## 2. Core Responsibilities & Workflow
1. **Audit Confidence Ratings:** Verify that notes claiming `VERIFIED` status have verified discovery reports in `50_operations_and_knowledge/54_ai_discovery/`.
2. **Detect Outdated & Missing Knowledge:** Flag unverified IPs, missing VLANs, or outdated documentation.
3. **Audit Multi-Device Paths:** Identify SPOFs across firewall links, F5 VIPs, ESXi host co-location, and storage LUNs.
4. **Generate Quality Audit Reports:** Commit recommendations to `50_operations_and_knowledge/54_ai_discovery/`.
