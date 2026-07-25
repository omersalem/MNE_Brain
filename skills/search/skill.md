---
name: "search"
description: "Search vault notes for Search and Learn intents. Escalates to Investigation Mode when queried objects are unverified."
---

# Skill: Search (`skills/search/skill.md`)

> **Inheritance:** Extends `[[AGENTS.md]]` and `[[base-agent.md]]`.

## 1. Purpose
Search the Brain for infrastructure objects. Responds to **Search** and **Learn** intents using Quick Mode; escalates to Investigation Mode when queried objects are unverified or missing.

## 2. Intent-Based Workflow
- **Search / Learn Intent (Quick Mode):** Search domain notes, profiles, and runbooks. Return concise findings with Wiki citations and confidence ratings.
- **Escalation to Investigation Mode:** If object (IP, MAC, VM, VLAN) is missing or unverified, escalate to Investigation Mode, recommend read-only Live Verification, and attach a Verification Summary.
