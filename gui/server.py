#!/usr/bin/env python3
"""
MNE_Brain Release 2 — Presentation GUI Server (`gui/server.py`)
MANDATORY ARCHITECTURAL RULE: ZERO Business Logic in GUI. Presentation ONLY.
Delegates HTTP serving and REST API requests to core.api.server.
"""

import sys
from pathlib import Path

# Add project root to sys.path
base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

from core.api.server import run_api_server

def run_presentation_server(port: int = 8080):
    print(f"Starting MNE_Brain Presentation GUI Server on port {port} (ZERO Business Logic in GUI)...")
    run_api_server(port=port)

if __name__ == "__main__":
    run_presentation_server()
