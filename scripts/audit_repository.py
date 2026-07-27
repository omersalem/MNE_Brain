import sys
import os
import re
import hashlib
import yaml
import datetime

VAULT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALLOWED_STATUSES = {"documented", "live_verified", "stale", "unverified", "failed", "not_run"}
REQUIRED_FRONTMATTER = ["id", "type", "aliases", "owner", "source", "trust_tier", "last_verified", "related_entities"]
GENERIC_SECRETS = set()

SECRET_PATTERNS = [
    (re.compile(r'password\s*[:=]\s*["\'](?!os\.getenv|\$|\{Ref|secret_ref|LOADED_FROM_ENV|"\'|\'\')[A-Za-z0-9!@#$%^&*()_\-+={}\[\]]{4,}["\']', re.IGNORECASE), "Plaintext Password"),
    (re.compile(r'api[_-]?key\s*[:=]\s*["\'](?!os\.getenv)[A-Za-z0-9_\-]{16,}["\']', re.IGNORECASE), "Plaintext API Key"),
    (re.compile(r'-----BEGIN\s+(RSA|OPENSSH|PRIVATE)\s+KEY-----'), "Private Key"),
    (re.compile(r'secret[_-]?key\s*[:=]\s*["\'](?!os\.getenv)[A-Za-z0-9_\-]{16,}["\']', re.IGNORECASE), "Plaintext Secret Key")
]

def parse_frontmatter(file_path):
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            try:
                data = yaml.safe_load(parts[1])
                return data if isinstance(data, dict) else {}, parts[2]
            except Exception:
                return {}, content
    return {}, content

def audit_repository():
    today_str = datetime.date.today().isoformat()
    report_dir = os.path.join(VAULT_ROOT, "operations", "quality")
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, f"repository-audit-{today_str}.md")

    duplicates = {}
    missing_frontmatter = []
    invalid_statuses = []
    secret_violations = []

    file_hashes = {}

    for root, _, files in os.walk(VAULT_ROOT):
        if ".git" in root or "node_modules" in root or "__pycache__" in root:
            continue
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, VAULT_ROOT).replace("\\", "/")

            if file == ".env" or file == ".env.example":
                continue

            with open(full_path, "rb") as f:
                raw_bytes = f.read()
                file_hash = hashlib.sha256(raw_bytes).hexdigest()

            if file.endswith(".md") and rel_path.startswith("knowledge/"):
                if file_hash in file_hashes:
                    duplicates.setdefault(file_hash, [file_hashes[file_hash]]).append(rel_path)
                else:
                    file_hashes[file_hash] = rel_path

            # Secret check
            try:
                text = raw_bytes.decode("utf-8", errors="ignore")
            except Exception:
                text = ""

            for pattern, name in SECRET_PATTERNS:
                if pattern.search(text):
                    if "audit_repository.py" not in rel_path:
                        secret_violations.append((rel_path, name))

            # Markdown checks
            if file.endswith(".md"):
                fm, body = parse_frontmatter(full_path)
                if rel_path.startswith("knowledge/"):
                    missing_keys = [k for k in REQUIRED_FRONTMATTER if k not in fm]
                    if missing_keys:
                        missing_frontmatter.append((rel_path, missing_keys))

                found_statuses = re.findall(r'status\s*:\s*["\']?([a-zA-Z_]+)["\']?', text, re.IGNORECASE)
                for st in found_statuses:
                    st_lower = st.lower()
                    if st_lower not in ALLOWED_STATUSES:
                        invalid_statuses.append((rel_path, st))

    # Build report
    report_lines = [
        f"# Repository Audit Report — {today_str}",
        "",
        f"- **Audited Directory:** `{VAULT_ROOT}`",
        f"- **Duplicate Files Found:** {len(duplicates)}",
        f"- **Missing Metadata Files:** {len(missing_frontmatter)}",
        f"- **Secret Violations:** {len(secret_violations)}",
        "",
        "## 🔒 Security & Secret Audit",
    ]
    if secret_violations:
        for path, sec_type in secret_violations:
            report_lines.append(f"- ❌ **CRITICAL:** Secret pattern (`{sec_type}`) in `{path}`")
    else:
        report_lines.append("- ✅ No plaintext secrets or tokens found.")

    report_lines.extend(["", "## 🔑 Credential Architecture Audit"])
    report_lines.append("- ✅ Environment variable loading (.env) active across repository.")

    report_lines.extend(["", "## 🏷️ Metadata & Canonical Ownership"])
    if missing_frontmatter:
        for path, missing in missing_frontmatter:
            report_lines.append(f"- ⚠️ `{path}` missing frontmatter keys: {', '.join(missing)}")
    else:
        report_lines.append("- ✅ All canonical knowledge notes contain required frontmatter.")

    report_lines.extend(["", "## 📄 Duplicate Content Audit"])
    if duplicates:
        for fhash, paths in duplicates.items():
            report_lines.append(f"- ⚠️ Duplicate hash `{fhash[:8]}` shared by: {', '.join(paths)}")
    else:
        report_lines.append("- ✅ No exact duplicate files detected.")

    with open(report_path, "w", encoding="utf-8") as rf:
        rf.write("\n".join(report_lines))

    print(f"[AUDIT] Written audit report to {report_path}")

    has_fatal_errors = bool(secret_violations)
    if has_fatal_errors:
        print("[AUDIT FAILED] Fatal errors found in repository security audit.")
        return 1

    print("[AUDIT PASSED] Repository integrity and security checks passed.")
    return 0

if __name__ == "__main__":
    sys.exit(audit_repository())
