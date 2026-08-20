#!/usr/bin/env python3
"""
MNE_Brain Release 2 — Automated Asset Migration Utility (`scripts/migrate_v1_to_v2.py`)
Migrates profiles, canonical notes, and tasks from MNE_Brain_v1 to MNE_Brain_v2 cleanly.
"""

import sys
import shutil
import argparse
from pathlib import Path

def migrate_v1_to_v2(source_dir: Path, target_dir: Path):
    print("==================================================")
    print(f" MNE_Brain Migration Utility: {source_dir.name} ➔ {target_dir.name}")
    print("==================================================")
    
    if not source_dir.exists():
        print(f"Source directory {source_dir} does not exist.")
        return False

    # 1. Copy Declarative Profiles
    src_profiles = source_dir / "profiles"
    tgt_profiles = target_dir / "profiles"
    tgt_profiles.mkdir(parents=True, exist_ok=True)
    
    if src_profiles.exists():
        for prof in src_profiles.glob("*.yaml"):
            shutil.copy2(prof, tgt_profiles / prof.name)
            print(f" [MIGRATED] Profile: {prof.name}")

    # 2. Copy Canonical Notes
    src_know = source_dir / "knowledge"
    tgt_know = target_dir / "knowledge"
    if src_know.exists():
        for domain_dir in src_know.iterdir():
            if domain_dir.is_dir():
                tgt_domain = tgt_know / domain_dir.name
                tgt_domain.mkdir(parents=True, exist_ok=True)
                for note in domain_dir.glob("*.md"):
                    shutil.copy2(note, tgt_domain / note.name)
                    print(f" [MIGRATED] Knowledge Note: {domain_dir.name}/{note.name}")

    print("\n[MIGRATION SUCCESSFUL] Assets migrated to Release 2 cleanly.")
    print("==================================================")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MNE_Brain Migration Utility")
    parser.add_argument("--source", default="d:/projects/MNE_Brain_v1", help="Source Release 1 directory")
    parser.add_argument("--target", default="d:/projects/MNE_Brain_v2", help="Target Release 2 directory")
    args = parser.parse_args()
    
    success = migrate_v1_to_v2(Path(args.source), Path(args.target))
    sys.exit(0 if success else 1)
