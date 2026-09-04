#!/usr/bin/env python3
"""Validate simple Git-based containment without reading or printing secret values."""

import subprocess
import sys
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent.parent
SENSITIVE_ENV_KEYS = {
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "DEEPSEEK_API_KEY",
    "FORTIGATE_CREDENTIAL_REF",
    "MNE_FORTIGATE_CREDENTIAL_ENV_FILE",
    "MNE_FORTIGATE_HOST_KEY",
    "MNE_FORTIGATE_USERNAME_KEY",
    "MNE_FORTIGATE_PASSWORD_KEY",
    "MNE_FORTIGATE_SSH_HOSTKEY",
    "CISCO_CREDENTIAL_REF",
    "VMWARE_CREDENTIAL_REF",
}
IGNORE_PROBES = (
    ".env",
    ".env.local",
    ".env.production",
    "config/chatgpt_oauth_tokens.json",
    "config/api_keys_storage.json",
    "config/local_credentials.json",
    "config/local_secrets.json",
    "local-private.key",
    "local-certificate.pem",
)


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=BASE_DIR,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def _is_sensitive_tracked_path(path: str) -> bool:
    normalized = path.replace("\\", "/").casefold()
    name = normalized.rsplit("/", 1)[-1]
    if name == ".env" or name.startswith(".env."):
        return name != ".env.example"
    if name.endswith((".pem", ".key")):
        return True
    return normalized.startswith("config/") and any(
        marker in name for marker in ("token", "key", "credential", "secret")
    )


def validate_p0_containment() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    ignore_lines = {
        line.strip()
        for line in (BASE_DIR / ".gitignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    required_rules = {".env", ".env.*", "!.env.example"}
    checks.append(
        {
            "name": "required_env_ignore_rules",
            "passed": required_rules.issubset(ignore_lines),
            "detail": "Local .env variants are ignored and the blank example remains allowed.",
        }
    )

    ignored_probes = []
    for probe in IGNORE_PROBES:
        result = _git("check-ignore", "--no-index", "-q", "--", probe)
        ignored_probes.append(result.returncode == 0)
    checks.append(
        {
            "name": "git_ignore_behavior",
            "passed": all(ignored_probes),
            "detail": f"Git ignored {sum(ignored_probes)} of {len(ignored_probes)} local-secret probes.",
        }
    )

    tracked = _git("ls-files", "-z")
    tracked_paths = [item for item in tracked.stdout.split("\0") if item]
    sensitive_tracked = [path for path in tracked_paths if _is_sensitive_tracked_path(path)]
    checks.append(
        {
            "name": "no_tracked_local_secrets",
            "passed": tracked.returncode == 0 and not sensitive_tracked,
            "detail": (
                "No local secret file is tracked."
                if not sensitive_tracked
                else f"Sensitive tracked paths detected: {len(sensitive_tracked)}"
            ),
        }
    )

    example_path = BASE_DIR / ".env.example"
    example_values: dict[str, str] = {}
    for raw_line in example_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        example_values[key.strip()] = value.strip()
    populated_sensitive = [
        key for key in SENSITIVE_ENV_KEYS if example_values.get(key, "")
    ]
    checks.append(
        {
            "name": "blank_environment_example",
            "passed": not populated_sensitive,
            "detail": (
                "Credential fields in .env.example are blank."
                if not populated_sensitive
                else f"Populated credential fields detected: {len(populated_sensitive)}"
            ),
        }
    )

    local_token_path = BASE_DIR / "config" / "chatgpt_oauth_tokens.json"
    token_ignored = not local_token_path.exists() or _git(
        "check-ignore", "--no-index", "-q", "--", "config/chatgpt_oauth_tokens.json"
    ).returncode == 0
    checks.append(
        {
            "name": "existing_local_token_contained",
            "passed": token_ignored,
            "detail": "Existing local token storage is absent or ignored; values were not read.",
        }
    )

    passed = sum(1 for check in checks if check["passed"])
    return {
        "success": passed == len(checks),
        "mode": "P0_SIMPLE_GIT_CONTAINMENT",
        "passed": passed,
        "total": len(checks),
        "secret_values_read": False,
        "secret_values_printed": False,
        "credential_rotation_required": False,
        "vault_required": False,
        "checks": checks,
    }


if __name__ == "__main__":
    report = validate_p0_containment()
    print("=" * 68)
    print(" MNE_Brain P0 - Simple Local Secret Containment")
    print("=" * 68)
    for check in report["checks"]:
        print(f"[{'PASS' if check['passed'] else 'FAIL'}] {check['name']} | {check['detail']}")
    print("=" * 68)
    print(f" P0 CONTAINMENT: {report['passed']} / {report['total']} CHECKS PASSED")
    print(" Secret values read: no | Secret values printed: no")
    print("=" * 68)
    sys.exit(0 if report["success"] else 1)
