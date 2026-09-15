#!/usr/bin/env python3
"""
Road Hazard Detection - Admin Account Creation Script.
Creates a new administrator account with a securely hashed password using Argon2.
"""

import sys
import argparse
import getpass
from pathlib import Path
from pwdlib import PasswordHash

# Add project root directory to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.database import SessionLocal
from backend.models.admin import Admin

def create_admin(username=None):
    print("=" * 80)
    print("ROAD HAZARD - ADMIN ACCOUNT CREATOR")
    print("=" * 80)

    if not username:
        username = input("Enter administrator username: ").strip()
    else:
        username = username.strip()

    if not username or len(username) > 50:
        print("[Error] Username must be between 1 and 50 characters.")
        return False

    # Get password interactively
    password = getpass.getpass("Enter administrator password: ")
    if len(password) < 12 or len(password) > 256:
        print("[Error] Password must be between 12 and 256 characters long.")
        return False

    confirm_password = getpass.getpass("Confirm password: ")
    if password != confirm_password:
        print("[Error] Passwords do not match.")
        return False

    db = SessionLocal()
    try:
        # Check if username already exists
        existing_admin = db.query(Admin).filter(Admin.username == username).first()
        if existing_admin:
            print(f"[Error] Admin user '{username}' already exists.")
            return False

        # Hash the password using Argon2
        password_hash = PasswordHash.recommended()
        hashed_password = password_hash.hash(password)

        # Create the new admin
        new_admin = Admin(
            username=username,
            password_hash=hashed_password,
            is_active=True
        )

        db.add(new_admin)
        db.commit()
        print(f"[OK] Admin user '{username}' created successfully.")
        return True

    except Exception as e:
        db.rollback()
        print(f"[Failed] Could not create admin account: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a new admin account.")
    parser.add_argument("--username", required=False, help="Administrator username")
    # No --password argument to ensure it's not stored in bash history

    args = parser.parse_args()

    success = create_admin(args.username)
    if not success:
        sys.exit(1)
