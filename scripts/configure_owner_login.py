#!/usr/bin/env python3
"""Configure the single local GUI owner without printing the password or hash."""

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.api.security import OwnerCredentialVerifier
from core.credentials import CredentialStore


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", default="", help="Local owner username; prompted when omitted")
    args = parser.parse_args()
    username = args.username.strip() or input("Owner username: ").strip()
    if not 3 <= len(username) <= 80 or any(character.isspace() for character in username):
        print("Owner username must contain 3-80 non-space characters.")
        return 2
    password = getpass.getpass("Owner password (12+ characters): ")
    confirmation = getpass.getpass("Confirm owner password: ")
    if password != confirmation:
        print("Passwords did not match.")
        return 2
    try:
        password_hash = OwnerCredentialVerifier.hash_password(password)
    except ValueError as exc:
        print(str(exc))
        return 2
    finally:
        password = ""
        confirmation = ""
    store = CredentialStore(BASE_DIR)
    username_storage = store.set("MNE_OWNER_USERNAME", username)
    hash_storage = store.set("MNE_OWNER_PASSWORD_HASH", password_hash)
    password_hash = ""
    print(f"Owner login configured. Username storage: {username_storage}; password-hash storage: {hash_storage}.")
    print("Restart the GUI server. No plaintext password was stored by this script.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
