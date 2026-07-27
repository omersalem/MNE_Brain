import sys
import os
import argparse
import json
import yaml
import datetime

VAULT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, VAULT_ROOT)

from scripts.route_query import route_query
from scripts.build_entity_index import resolve_entity

class EvidencePackBuilder:
    """
    Evidence Pack Builder for MNE Brain.
    Slices knowledge & evidence based on query route and entity resolution.
    Designed for future Knowledge Summary Cache integration by decoupling full file loads
    from structured summary snippets.
    """
    def __init__(self, vault_root=VAULT_ROOT):
        self.vault_root = vault_root

    def _read_file_snippet(self, rel_path, max_chars=1200):
        full_path = os.path.join(self.vault_root, rel_path)
        if not os.path.exists(full_path):
            return "", f"File missing: {rel_path}"

        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()

        # Decoupled Summary Extraction Abstraction (Future Knowledge Summary Cache ready)
        summary = ""
        if "---" in text:
            parts = text.split("---", 2)
            if len(parts) >= 3:
                body = parts[2].strip()
            else:
                body = text.strip()
        else:
            body = text.strip()

        # Extract top 3 bullet points or first paragraph as summary if available
        summary_lines = [l for l in body.splitlines() if l.strip().startswith("-") or l.strip().startswith("1.")][:3]
        if summary_lines:
            summary = " ".join(summary_lines).replace("- ", "").strip()

        snippet = body[:max_chars] + ("\n...[Truncated]" if len(body) > max_chars else "")
        return snippet, summary

    def build_pack(self, question, target_entity_query=None):
        route_info = route_query(question)
        route = route_info["route"]
        requires_entity = route_info["requires_entity_resolution"]

        resolved_entities = []
        unknowns = []
        evidence_items = []

        if target_entity_query or requires_entity:
            target = target_entity_query or question
            res = resolve_entity(target)

            if res["status"] == "exact_match":
                resolved_entities.append(res["entity"])
            elif res["status"] == "ambiguous":
                resolved_entities.extend(res["candidates"])
                unknowns.append(f"Ambiguous target: '{target}'. Resolved to candidates: {[c['id'] for c in res['candidates']]}")
            else:
                unknowns.append(f"Target entity '{target}' not found in entity index.")

        # Gather evidence items based on resolved entities or query route
        if resolved_entities:
            for ent in resolved_entities:
                note_path = ent["canonical_note"]
                snippet, summary = self._read_file_snippet(note_path)
                evidence_items.append({
                    "id": ent["id"],
                    "source": f"canonical_note: {note_path}",
                    "trust_tier": ent.get("trust_tier", 3),
                    "observed_at": ent.get("last_verified", datetime.date.today().isoformat()),
                    "freshness": "documented",
                    "summary": summary,
                    "content_snippet": snippet
                })
        else:
            # Concept query (e.g. "Explain Exchange DAG"): search knowledge notes for relevant terms
            matches_found = False
            k_dir = os.path.join(self.vault_root, "knowledge")
            q_keywords = [w for w in question.lower().split() if len(w) > 3]

            for root, _, files in os.walk(k_dir):
                for file in files:
                    if file.endswith(".md"):
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, self.vault_root).replace("\\", "/")
                        snippet, summary = self._read_file_snippet(rel_path, max_chars=800)

                        if any(kw in snippet.lower() for kw in q_keywords):
                            matches_found = True
                            evidence_items.append({
                                "id": os.path.splitext(file)[0],
                                "source": f"canonical_note: {rel_path}",
                                "trust_tier": 3,
                                "observed_at": datetime.date.today().isoformat(),
                                "freshness": "documented",
                                "summary": summary,
                                "content_snippet": snippet
                            })
                            if len(evidence_items) >= 3:
                                break
                if matches_found and len(evidence_items) >= 3:
                    break

            if not evidence_items:
                unknowns.append(f"No specific knowledge document matched question keywords: {q_keywords}")

        # Check for live evidence in operations/evidence
        evidence_dir = os.path.join(self.vault_root, "operations", "evidence")
        if os.path.exists(evidence_dir):
            for ef in os.listdir(evidence_dir):
                if ef.endswith(".json"):
                    ef_path = os.path.join(evidence_dir, ef)
                    with open(ef_path, "r", encoding="utf-8") as f:
                        ev_data = json.load(f)
                    evidence_items.append({
                        "id": ev_data.get("evidence_id", ef),
                        "source": f"live_adapter: {ev_data.get('check_id', 'live_verify')}",
                        "trust_tier": 5,
                        "observed_at": ev_data.get("timestamp", datetime.date.today().isoformat()),
                        "freshness": "live_verified",
                        "summary": ev_data.get("summary", "Live telemetry collected from read-only adapter."),
                        "content_snippet": json.dumps(ev_data.get("normalized_output", {}), indent=2)
                    })

        pack = {
            "question": question,
            "query_route": route,
            "resolved_entities": resolved_entities,
            "evidence_items": evidence_items,
            "unknowns": unknowns,
            "generated_at": datetime.datetime.now().isoformat()
        }
        return pack

def main():
    parser = argparse.ArgumentParser(description="Evidence Pack Builder for MNE Brain")
    parser.add_argument("--question", required=True, help="Question string")
    parser.add_argument("--target", help="Target entity ID or name")
    args = parser.parse_args()

    builder = EvidencePackBuilder()
    pack = builder.build_pack(args.question, args.target)
    print(json.dumps(pack, indent=2))

if __name__ == "__main__":
    main()
