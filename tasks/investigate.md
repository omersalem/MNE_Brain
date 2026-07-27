# Task: Investigation Planning Engine (`tasks/investigate.md`)

> **Phase D.5 Requirement:** Before any live verification or troubleshooting commands are executed, the AI Agent MUST generate an Investigation Plan adhering to `00_meta/03_ai_contracts/investigation-plan-schema.yaml`.

## Operational Workflow
1. Receive Query Route & Evidence Pack.
2. Evaluate if Knowledge Base evidence is sufficient to answer with High confidence.
   - If YES ➔ Set `is_live_verification_required: false` and proceed directly to Dynamic Answer Template.
   - If NO ➔ Identify missing unknown variables.
3. Formulate competing hypotheses.
4. Perform **Highest Information Gain Analysis**: Select the single highest-value read-only check that bisects the problem space.
5. Define explicit **Stop Conditions** to halt further live checks immediately upon hypothesis confirmation or rejection.
6. Hand off the structured Investigation Plan for targeted read-only verification.
