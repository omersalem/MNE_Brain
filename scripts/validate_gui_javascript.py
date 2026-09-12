#!/usr/bin/env python3
"""Syntax-check every modular P11 presentation script without serving it."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def validate() -> bool:
    base = Path(__file__).resolve().parent.parent
    node = shutil.which("node")
    if not node:
        print("GUI JavaScript validation failed: node is unavailable")
        return False
    scripts = sorted((base / "gui/scripts").glob("*.js"))
    required = {"api.js", "auth.js", "threads.js", "composer.js", "streaming.js", "activity.js", "evidence.js", "tool_calls.js", "approvals.js", "providers.js", "p10.js", "security_agent.js"}
    if {path.name for path in scripts} != required:
        print("GUI JavaScript validation failed: P11 module inventory mismatch")
        return False
    for script in scripts:
        result = subprocess.run([node, "--check", str(script)], text=True, capture_output=True, check=False)
        if result.returncode:
            print(f"{script.name}: {result.stderr.strip()}")
            return False
    print(f"GUI JavaScript syntax passed ({len(scripts)} modules)")
    return True


if __name__ == "__main__":
    sys.exit(0 if validate() else 1)
