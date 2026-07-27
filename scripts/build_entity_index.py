import sys
import os
import re
import json
import yaml
import datetime

VAULT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KNOWLEDGE_DIR = os.path.join(VAULT_ROOT, "knowledge")
INDEX_OUTPUT_PATH = os.path.join(VAULT_ROOT, "00_meta", "04_indices", "entity-index.json")
REPORT_OUTPUT_DIR = os.path.join(VAULT_ROOT, "operations", "quality")

class EntityIndexBuilder:
    """
    Modular Entity Index Builder designed for Future Scalability.
    Builds structured sub-indices (IP, Hostname, Service, Application, Branch, VLAN)
    and serializes to entity-index.json.
    """
    def __init__(self, vault_root=VAULT_ROOT):
        self.vault_root = vault_root
        self.entities = {}
        self.ip_index = {}
        self.hostname_index = {}
        self.service_index = {}
        self.application_index = {}
        self.branch_index = {}
        self.vlan_index = {}
        self.conflicts = []

    def parse_frontmatter(self, file_path):
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    fm = yaml.safe_load(parts[1])
                    return fm if isinstance(fm, dict) else {}, parts[2]
                except Exception:
                    return {}, content
        return {}, content

    def scan_knowledge(self):
        for root, _, files in os.walk(KNOWLEDGE_DIR):
            for file in files:
                if file.endswith(".md"):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, self.vault_root).replace("\\", "/")
                    fm, body = self.parse_frontmatter(full_path)

                    entity_id = fm.get("id") or os.path.splitext(file)[0]
                    entity_type = fm.get("type") or "resource"
                    aliases = [str(a) for a in fm.get("aliases", [entity_id])]
                    base_name = os.path.splitext(file)[0]
                    if entity_id not in aliases:
                        aliases.append(entity_id)
                    if base_name not in aliases:
                        aliases.append(base_name)

                    # Extract IPs, FQDNs, Services, Site, VLANs from frontmatter or content regex
                    ips = fm.get("ips") or list(set(re.findall(r'\b(?:172\.\d{1,3}|10\.\d{1,3}|192\.168)\.\d{1,3}\.\d{1,3}\b', body)))
                    fqdns = fm.get("fqdns") or list(set(re.findall(r'\b[a-zA-Z0-9_-]+\.mne\.gov(?:\.ps)?\b', body)))
                    services = fm.get("services") or ([entity_type] if entity_type in ["firewall", "vpn", "dns", "exchange"] else [])
                    site = fm.get("site") or ("HQ" if "hq" in entity_id.lower() or "hq" in rel_path.lower() else "Branch")
                    vlans = fm.get("vlans") or [int(v) for v in re.findall(r'\bVLAN\s*(\d+)\b', body, re.IGNORECASE)]

                    record = {
                        "id": entity_id,
                        "type": entity_type,
                        "canonical_note": rel_path,
                        "aliases": sorted(list(set(aliases))),
                        "ips": sorted(list(set(ips))),
                        "fqdns": sorted(list(set(fqdns))),
                        "services": sorted(list(set(services))),
                        "site": site,
                        "vlans": sorted(list(set(vlans))),
                        "related_entities": sorted(list(set(fm.get("related_entities", [])))),
                        "trust_tier": fm.get("trust_tier", 3),
                        "last_verified": fm.get("last_verified", datetime.date.today().isoformat())
                    }

                    if entity_id in self.entities:
                        self.conflicts.append(f"Duplicate entity ID: {entity_id}")
                    else:
                        self.entities[entity_id] = record
                        self._index_subcomponents(record)

    def _index_subcomponents(self, record):
        entity_id = record["id"]

        # IP Indexing
        for ip in record["ips"]:
            self.ip_index.setdefault(ip, []).append(entity_id)

        # Hostname/Alias Indexing
        for alias in record["aliases"] + record["fqdns"]:
            alias_lower = alias.lower()
            self.hostname_index.setdefault(alias_lower, []).append(entity_id)

        # Service Indexing
        for svc in record["services"]:
            self.service_index.setdefault(svc.lower(), []).append(entity_id)

        # Branch / Site Indexing
        if record["site"]:
            self.branch_index.setdefault(record["site"].lower(), []).append(entity_id)

        # VLAN Indexing
        for v in record["vlans"]:
            self.vlan_index.setdefault(str(v), []).append(entity_id)

    def build_and_save(self, output_path=INDEX_OUTPUT_PATH):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        master_index = {
            "version": "2.0",
            "generated_at": datetime.datetime.now().isoformat(),
            "total_entities": len(self.entities),
            "sub_indices": {
                "ips": self.ip_index,
                "hostnames": self.hostname_index,
                "services": self.service_index,
                "branches": self.branch_index,
                "vlans": self.vlan_index
            },
            "entities": self.entities
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(master_index, f, indent=2, sort_keys=True)

        print(f"[ENTITY INDEX] Built master index at {output_path} with {len(self.entities)} entities.")
        return master_index

    def generate_report(self):
        today_str = datetime.date.today().isoformat()
        os.makedirs(REPORT_OUTPUT_DIR, exist_ok=True)
        report_path = os.path.join(REPORT_OUTPUT_DIR, f"entity-index-report-{today_str}.md")

        lines = [
            f"# Entity Index Build Report — {today_str}",
            "",
            f"- **Total Entities Indexed:** {len(self.entities)}",
            f"- **Indexed IPs:** {len(self.ip_index)}",
            f"- **Indexed Hostnames/Aliases:** {len(self.hostname_index)}",
            f"- **Indexed Services:** {len(self.service_index)}",
            f"- **Conflicts Detected:** {len(self.conflicts)}",
            "",
            "## 📋 Entity Inventory Summary"
        ]
        for eid, rec in sorted(self.entities.items()):
            lines.append(f"- `{eid}` ({rec['type']}) ➔ `{rec['canonical_note']}` [IPs: {', '.join(rec['ips']) or 'None'}]")

        with open(report_path, "w", encoding="utf-8") as rf:
            rf.write("\n".join(lines))
        print(f"[REPORT] Entity index report written to {report_path}")

def resolve_entity(query_term, index_path=INDEX_OUTPUT_PATH):
    """
    Deterministic Entity Resolver function.
    """
    if not os.path.exists(index_path):
        return {"status": "error", "message": "Entity index not built"}

    with open(index_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    entities = data.get("entities", {})
    sub_indices = data.get("sub_indices", {})
    q_lower = query_term.lower()

    # Direct ID match
    if query_term in entities:
        return {"status": "exact_match", "entity": entities[query_term]}

    # Hostname/Alias lookup
    matches = set()
    if q_lower in sub_indices.get("hostnames", {}):
        matches.update(sub_indices["hostnames"][q_lower])

    # IP lookup
    if query_term in sub_indices.get("ips", {}):
        matches.update(sub_indices["ips"][query_term])

    # Substring search in aliases
    if not matches:
        for eid, rec in entities.items():
            if any(q_lower in a.lower() for a in rec["aliases"]):
                matches.add(eid)

    match_list = list(matches)
    if len(match_list) == 1:
        return {"status": "exact_match", "entity": entities[match_list[0]]}
    elif len(match_list) > 1:
        candidates = [entities[m] for m in match_list[:3]]
        return {"status": "ambiguous", "candidates": candidates}
    else:
        return {"status": "unknown", "query": query_term}

def main():
    builder = EntityIndexBuilder()
    builder.scan_knowledge()
    builder.build_and_save()
    builder.generate_report()

if __name__ == "__main__":
    main()
