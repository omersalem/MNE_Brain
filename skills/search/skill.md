---
name: "search"
description: "Search across all vault notes, profiles, runbooks, and graph links. Automatically triggers Live Verification for missing objects."
---

# Skill: Search (`skills/search/skill.md`)

> **Inheritance:** Extends `[[AGENTS.md]]` and `[[base-agent.md]]`.

## 1. Purpose
Search the entire Brain for infrastructure objects. If an object cannot be found in static notes, automatically evaluates whether Live Verification can locate it on live infrastructure.

## 2. Embedded Live Verification Workflow
1. **Traverse Vault Indices & Canonical Notes:** Search `00_meta/04_indices/`, domain notes, Connection Profiles, Runbooks, and Incident logs.
2. **Evaluate Search Confidence:** If object (IP, hostname, firewall object, route, VLAN, VM, DNS record, interface, server) is found, rank relevance and cite sources with Wiki links (`[[Entity-Basename]]`).
3. **Trigger Embedded Live Verification:** If object is **not found**, do NOT conclude it does not exist. Check available connectors and recommend read-only Live Verification (ARP tables, MAC tables, vCenter API, DNS query, WinRM, OpenSSH) before delivering conclusions.
4. **Present Grounded Findings:** State confidence explicitly (`VERIFIED`, `HIGH`, `MEDIUM`, `LOW`). Never invent search results.
