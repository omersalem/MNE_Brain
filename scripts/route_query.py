import sys
import os
import argparse
import json
import re
import yaml

VAULT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULES_PATH = os.path.join(VAULT_ROOT, "00_meta", "03_ai_contracts", "query-routing-rules.yaml")

ROUTE_EVIDENCE_MAP = {
    "asset_lookup": ["canonical_asset"],
    "topology": ["canonical_asset", "path_dependencies"],
    "explanation": ["canonical_facts", "linked_diagram_notes"],
    "incident": ["canonical_asset", "recent_incidents", "known_impact"],
    "troubleshooting": ["canonical_asset", "path_dependencies", "runbook", "targeted_checks"],
    "health_check": ["canonical_asset", "permitted_live_profile"],
    "documentation": ["canonical_note", "official_manual"],
    "review": ["metadata", "link", "freshness", "duplicate_reports"],
    "remediation": ["verified_cause", "action_policy", "approved_template"]
}

def route_query(question):
    q_lower = question.lower()

    if os.path.exists(RULES_PATH):
        with open(RULES_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        rules = data.get("rules", [])
        default_rule = data.get("default_route", {})
    else:
        rules = []
        default_rule = {"route": "explanation", "requires_entity_resolution": False, "live_check_allowed": False, "remediation_gate_required": False}

    for rule in rules:
        keywords = rule.get("keywords", [])
        for kw in keywords:
            # Check for multi-word or single-word boundary match
            pattern = r'\b' + re.escape(kw) + r'\b' if ' ' not in kw else re.escape(kw)
            if re.search(pattern, q_lower):
                route = rule["route"]
                return {
                    "question": question,
                    "route": route,
                    "requires_entity_resolution": rule.get("requires_entity_resolution", True),
                    "evidence_requirements": ROUTE_EVIDENCE_MAP.get(route, ["canonical_facts"]),
                    "live_check_allowed": rule.get("live_check_allowed", False),
                    "remediation_gate_required": rule.get("remediation_gate_required", False)
                }

    # Default fallback
    route = default_rule.get("route", "explanation")
    return {
        "question": question,
        "route": route,
        "requires_entity_resolution": default_rule.get("requires_entity_resolution", False),
        "evidence_requirements": ROUTE_EVIDENCE_MAP.get(route, ["canonical_facts"]),
        "live_check_allowed": default_rule.get("live_check_allowed", False),
        "remediation_gate_required": default_rule.get("remediation_gate_required", False)
    }

def main():
    parser = argparse.ArgumentParser(description="Deterministic Query Router for MNE Brain")
    parser.add_argument("--question", required=True, help="User query question string")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    result = route_query(args.question)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
