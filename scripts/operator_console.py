#!/usr/bin/env python3
"""
MNE_Brain Release 2 — Operator Console CLI (`scripts/operator_console.py`)
Provides direct administrative access:
  1. Unrestricted Read / Diagnostics across all canonical assets.
  2. Governed Write Preparation with automated Risk Level classification and explicit Rollback Feasibility.
  3. Interactive Administrator Confirmation before write execution.
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.infrastructure.owner_direct import OwnerDirectService, OwnerDirectError
from core.entity.build_entity_index import EntityIndexBuilder


def get_owner_direct_service() -> OwnerDirectService:
    """Initialize OwnerDirectService with base directory."""
    return OwnerDirectService(BASE_DIR)


def cmd_list(args) -> None:
    """List canonical assets available in MNE_Brain."""
    entities = EntityIndexBuilder(BASE_DIR).build_index(persist=False)["entities"]
    print(f"\n{'ENTITY ID':<30} {'IP / TARGET':<18} {'CATEGORY':<14} {'HOSTNAME'}")
    print("=" * 80)
    for e in sorted(entities, key=lambda x: x.get("entity_id", "")):
        entity_id = e.get("entity_id", "")
        ip = e.get("ip", e.get("verification_target", ""))
        cat = e.get("category", "")
        hostname = e.get("hostname", "")
        print(f"{entity_id:<30} {ip:<18} {cat:<14} {hostname}")
    print(f"\nTotal Canonical Assets: {len(entities)}\n")


def cmd_read(args) -> None:
    """Run an unrestricted read / diagnostic command on a canonical asset."""
    service = get_owner_direct_service()
    print(f"\n[UNRESTRICTED READ] Targeting {args.entity} via {args.protocol}...")
    print(f"Command: {args.command}\n")

    try:
        result = service.discover(
            entity_id=args.entity,
            protocol=args.protocol,
            operation=args.command,
            target=args.target,
            owner_supplied_target=bool(args.target),
        )
    except OwnerDirectError as e:
        print(f"[-] Validation Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Status:             {result.get('status')}")
    print(f"Reachability:       {'REACHABLE' if result.get('reachability') else 'UNREACHABLE'}")
    print(f"Authentication:     {result.get('authentication_result')}")
    print(f"Identity Result:    {result.get('identity_result')}")
    print(f"Evidence ID:        {result.get('evidence_id')}")

    facts = result.get("facts", {})
    if facts:
        print("\n--- Facts Collected ---")
        print(json.dumps(facts, indent=2))
    elif result.get("status") == "ADAPTER_NOT_REGISTERED":
        print("\n[*] Note: Direct transport adapter is offline/unregistered in standalone CLI mode.")
        print(f"    Target is verified at {result.get('target')} for operation '{args.command}'.")


def cmd_write(args) -> None:
    """Prepare a write plan, display risk and rollback transparency, and confirm execution."""
    service = get_owner_direct_service()
    operations = [cmd.strip() for cmd in args.commands.split(";") if cmd.strip()]
    prechecks = [chk.strip() for chk in args.prechecks.split(";") if chk.strip()] if args.prechecks else ["Verify device connectivity"]
    postchecks = [chk.strip() for chk in args.postchecks.split(";") if chk.strip()] if args.postchecks else ["Verify configuration applied"]
    rollback_steps = [rb.strip() for rb in args.rollback.split(";") if rb.strip()] if args.rollback else []

    try:
        plan = service.prepare_write(
            entity_id=args.entity,
            protocol=args.protocol,
            operations=operations,
            intended_change=args.change or "Administrative configuration update",
            expected_impact=args.impact or "Device state update",
            downtime_risk=args.downtime or "Low/No downtime expected",
            blast_radius=args.blast_radius or f"Target asset {args.entity}",
            prechecks=prechecks,
            postchecks=postchecks,
            rollback_steps=rollback_steps,
            owner_requested=True,
        )
    except OwnerDirectError as e:
        print(f"[-] Plan Preparation Rejected: {e}", file=sys.stderr)
        sys.exit(1)

    warning = plan["warning"]
    can_rollback = plan.get("can_rollback", False)
    risk_level = plan.get("risk_level", "HIGH")

    print("\n" + "=" * 80)
    print("      ADMINISTRATOR RISK & ROLLBACK REVIEW — OWNER DIRECT WRITE")
    print("=" * 80)
    print(f" Plan ID:              {plan['plan_id']}")
    print(f" Target Asset:         {warning['target_device_system']}")
    print(f" Protocol:             {args.protocol.upper()}")
    print(f" Risk Level:           [{risk_level}]")
    if can_rollback:
        print(" Rollback Feasible:    [YES] Automated rollback steps are available.")
    else:
        print(" Rollback Feasible:    [NO] IRREVERSIBLE CHANGE — No automated rollback!")

    print("\n--- Intended Change ---")
    print(f" {warning['exact_intended_change']}")

    print("\n--- Operations to Apply ---")
    for idx, op in enumerate(operations, 1):
        print(f" {idx}. {op}")

    print("\n--- Impact & Blast Radius ---")
    print(f" Impact & Downtime:    {warning['expected_impact_and_downtime_risk']}")
    print(f" Blast Radius:         {warning['blast_radius']}")

    print("\n--- Prechecks & Postchecks ---")
    print(f" Prechecks:            {', '.join(warning['prechecks'])}")
    print(f" Postchecks:           {', '.join(warning['postchecks'])}")

    print("\n--- Rollback Details ---")
    print(f" Summary:              {warning['rollback_summary']}")
    if rollback_steps:
        for idx, rb in enumerate(rollback_steps, 1):
            print(f" {idx}. {rb}")
    else:
        print(" (No rollback commands specified. Manual intervention will be required if reverted.)")

    print("=" * 80)

    if not args.yes:
        confirm = input("\n[?] Authorize and apply this exact change now? [y/N]: ").strip().lower()
        if confirm not in {"y", "yes"}:
            print("[-] Write execution cancelled by administrator.")
            return

    # Execute confirmation
    session_digest = os.environ.get("MNE_OWNER_SESSION_DIGEST", "0" * 64)
    print(f"\n[*] Applying prepared write plan {plan['plan_id']}...")
    try:
        result = service.confirm_write(plan["plan_id"], owner_session_digest=session_digest)
        print(f"[+] Result: {result.get('status')}")
        print(f"    Postcheck Status: {result.get('postcheck_status')}")
        print(f"    Rollback Status:  {result.get('rollback_status')}")
    except OwnerDirectError as e:
        print(f"[-] Execution Error: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="MNE_Brain Administrator Operator Console")
    subparsers = parser.add_subparsers(dest="action", help="Action to perform")

    # List
    subparsers.add_parser("list", help="List all canonical entities")

    # Read
    read_parser = subparsers.add_parser("read", help="Run unrestricted diagnostic read command")
    read_parser.add_argument("--entity", required=True, help="Canonical entity ID (e.g. fw-fortigate-jenin-01)")
    read_parser.add_argument("--command", required=True, help="Command (e.g. 'diagnose vpn tunnel list')")
    read_parser.add_argument("--protocol", default="ssh", choices=["ssh", "rest", "powershell", "winrm", "snmp", "tcp"])
    read_parser.add_argument("--target", default=None, help="Optional override target IP/host")

    # Write
    write_parser = subparsers.add_parser("write", help="Prepare and confirm a write operation")
    write_parser.add_argument("--entity", required=True, help="Canonical entity ID")
    write_parser.add_argument("--commands", required=True, help="Semicolon-separated list of commands")
    write_parser.add_argument("--protocol", default="ssh", choices=["ssh", "rest", "powershell", "winrm"])
    write_parser.add_argument("--change", default="", help="Description of intended change")
    write_parser.add_argument("--impact", default="", help="Expected impact")
    write_parser.add_argument("--downtime", default="", help="Downtime risk assessment")
    write_parser.add_argument("--blast-radius", default="", help="Blast radius description")
    write_parser.add_argument("--prechecks", default="", help="Semicolon-separated precheck commands")
    write_parser.add_argument("--postchecks", default="", help="Semicolon-separated postcheck commands")
    write_parser.add_argument("--rollback", default="", help="Semicolon-separated rollback commands")
    write_parser.add_argument("--yes", "-y", action="store_true", help="Skip interactive confirmation prompt")

    args = parser.parse_args()
    if not args.action:
        parser.print_help()
        sys.exit(1)

    if args.action == "list":
        cmd_list(args)
    elif args.action == "read":
        cmd_read(args)
    elif args.action == "write":
        cmd_write(args)


if __name__ == "__main__":
    main()
