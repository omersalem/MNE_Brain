---
name: "search"
description: "Search Layer 1 knowledge/ and Layer 3 intelligence/. Uses Information Gain verification when queried objects are unverified."
---

# Skill: Search (`skills/search/skill.md`)

> **Inheritance:** Extends `[[AGENTS.md]]` and `[[base-agent.md]]`.

## 1. Purpose
Search the Brain for infrastructure objects. If an object is unverified or missing, uses Information Gain scoring to select the lowest-cost verification action.

## 2. Layered Workflow
1. **Search Layer 1 `knowledge/` & Layer 3 `intelligence/`:** Locate matching notes and Wiki links (`[[Entity-Basename]]`).
2. **Formulate Information Gain Plan:** If object (IP, MAC, VM, VLAN) is unverified, present Information Gain rating, Operational Cost, and Stop Conditions.
3. **Execute Read-Only Verification:** Conclude with standard Verification Summary block.
