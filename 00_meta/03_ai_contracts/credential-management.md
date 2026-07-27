# Credential Management & Resolution Specification

## Overview
MNE Brain enforces strict credential protection. Passwords, private keys, certificates, and API tokens MUST NEVER exist in tracked code, profiles, YAML files, or Markdown documentation.

All credentials are loaded exclusively from standard environment variables via `python-dotenv`.

## Standard Deployment Model

### 1. Environment Variable Storage (`.env`)
Local operational environment variables are stored in the root `.env` file:
```env
MNE_FORTIGATE_HOST=172.23.70.4
MNE_FORTIGATE_USERNAME=adminread
MNE_FORTIGATE_PASSWORD=<password>
```
The `.env` file is excluded from Git tracking via `.gitignore`.

### 2. Environment Template (`.env.example`)
`.env.example` is committed to version control and serves as the single schema template for local environment configuration. It contains no secret values or sensitive information.

### 3. Code Loading Pattern
All python scripts and adapters load environment variables using:
```python
import os
from dotenv import load_dotenv

load_dotenv()

host = os.getenv("MNE_FORTIGATE_HOST")
username = os.getenv("MNE_FORTIGATE_USERNAME")
password = os.getenv("MNE_FORTIGATE_PASSWORD")
```

### 4. Profiles & Documentation
Profiles in `profiles/` and documentation in `knowledge/` are documentation-only files and MUST NOT reference secret keys or contain passwords.
