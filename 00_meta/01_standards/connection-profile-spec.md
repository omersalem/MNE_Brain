---
id: "MNE-STD-CONN-SPEC"
title: "Connection Profile Specification & AI Rules"
type: "infrastructure_standard"
status: "active"
owner: "Lead-Architect"
last_review: "2026-07-24"
tags:
  - ministry/standards/connection
---

# Connection Profile Specification & AI Rules

Context: [[master-dashboard]] | Parent: [[index-standards]]

## Purpose
This document defines the rules for creating, maintaining, and using Markdown-based Connection Profiles for Ministry Infrastructure.

## AI Usage Guidelines
1. **Always Read Before Connecting:** The AI must inspect the corresponding `conn-*.md` note before launching any read-only discovery.
2. **Never Guess Attributes:** If `Password`, `Username`, or `Management IP` is empty or `PENDING`, the AI must ask the user for clarification.
3. **Strict Read-Only Enforcement:** Every profile MUST have `Access Level: Read-Only`.
4. **No Unconfirmed Overwrites:** The AI must never overwrite existing credentials without explicit user confirmation.

## Mandatory Validation Rules
- `Management IP` must be a valid IPv4 address in the Ministry subnet ranges (`172.23.X.X`).
- `Port` must match default service ports (SSH: 22, HTTPS: 443, WinRM: 5985/5986).
- `Access Level` must always be `Read-Only`.
