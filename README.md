# MNE Brain Repository (Version 2)

AI-Native Infrastructure Brain operating over Decoupled 3-Layer Architecture.

## Deployment & Setup

To deploy on another machine:

```bash
# 1. Clone repository
git clone <repository_url>

# 2. Copy .env file
cp .env.example .env

# 3. Install dependencies & Run
pip install -r requirements.txt
python scripts/validate_brain.py
```

> **Credential Policy**: All credentials are stored ONLY in the local `.env` file (`python-dotenv`). The `.env` file is never committed to Git. Only `.env.example` remains committed.

## System Workflow & Architecture
```
Question ➔ Query Router ➔ Entity Resolution (optional) ➔ Evidence Pack ➔ Investigation Planner ➔ Live Verification ➔ Dynamic Answer
```

## Key Configuration Files
- **Environment Template:** `.env.example` (Template for environment variable keys—NO SECRETS)
- **Routing Rules:** `00_meta/03_ai_contracts/query-routing-rules.yaml`
- **Action Policy:** `config/action_policy.yaml`

## Quick Commands
- **Audit Repository:** `python scripts/audit_repository.py`
- **Route Query:** `python scripts/route_query.py --question "<query>"`
- **Build Entity Index:** `python scripts/build_entity_index.py`
- **Build Evidence Pack:** `python scripts/build_evidence_pack.py --question "<query>"`
- **Live Verification:** `python scripts/live_verify.py --device fw-fortigate-hq-01 --check get_system_status`
- **Run Benchmarks:** `python scripts/run_benchmarks.py`
- **Full Validation:** `python scripts/validate_brain.py`
