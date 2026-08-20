#!/usr/bin/env python3
"""Acceptance test for the operator-approved simple P0 containment model."""

import sys
from pathlib import Path


base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

from scripts.validate_p0_containment import validate_p0_containment


def test_p0_simple_containment() -> None:
    report = validate_p0_containment()

    assert report["success"] is True
    assert report["passed"] == report["total"] == 5
    assert report["mode"] == "P0_SIMPLE_GIT_CONTAINMENT"
    assert report["secret_values_read"] is False
    assert report["secret_values_printed"] is False
    assert report["credential_rotation_required"] is False
    assert report["vault_required"] is False

    ignore_text = (base_dir / ".gitignore").read_text(encoding="utf-8")
    assert "\n.env\n" in f"\n{ignore_text}"
    assert ".env.*" in ignore_text
    assert "!.env.example" in ignore_text

    ci_text = (base_dir / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "scripts/validate_p0_containment.py" in ci_text
    assert (base_dir / "00_meta" / "adr" / "ADR-012-P0-Simple-Local-Secret-Containment.md").is_file()
    assert (base_dir / "docs" / "P0_SIMPLE_CONTAINMENT.md").is_file()
