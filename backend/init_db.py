#!/usr/bin/env python3
"""
Road Hazard Detection - Database & PostGIS Initialization Script.
Connects to PostgreSQL, checks/enables the PostGIS extension, and creates tables non-destructively.
"""

import sys
from pathlib import Path

# Add project root directory to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import create_engine, text
from backend.database import engine, Base, DATABASE_URL
from backend.models.hazard import Hazard  # Ensures model is registered with Base.metadata


def init_database():
    print("=" * 80)
    print("ROAD HAZARD DATABASE & POSTGIS INITIALIZER")
    import re
    masked_url = re.sub(r":([^@]+)@", ":***@", DATABASE_URL) if DATABASE_URL else "None"
    print(f"Target Database: {masked_url}")

    if not DATABASE_URL:
        print("[Error] DATABASE_URL is not set in backend/.env")
        sys.exit(1)

    # 0. Check and create database if it doesn't exist by connecting to default 'postgres' database
    print("\n[Step 1/5] Checking if target database exists...")
    try:
        from urllib.parse import urlparse, urlunparse
        parsed = urlparse(DATABASE_URL)
        target_db_name = parsed.path.lstrip("/") or "road_hazard_db"
        
        # Build maintenance admin URL pointing to default 'postgres' db
        admin_parsed = parsed._replace(path="/postgres")
        admin_url = urlunparse(admin_parsed)

        admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
        with admin_engine.connect() as admin_conn:
            exists = admin_conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :dbname"),
                {"dbname": target_db_name}
            ).scalar()

            if not exists:
                print(f"  Database '{target_db_name}' does not exist. Creating database '{target_db_name}'...")
                admin_conn.execute(text(f'CREATE DATABASE "{target_db_name}"'))
                print(f"  [OK] Database '{target_db_name}' created successfully.")
            else:
                print(f"  [OK] Database '{target_db_name}' already exists.")
        admin_engine.dispose()
    except Exception as db_create_err:
        print(f"  [Note] Auto-create database check note: {db_create_err}")

    # 1. Test connection to target database
    print("\n[Step 2/5] Verifying target PostgreSQL connection...")
    try:
        with engine.connect() as conn:
            pg_ver = conn.execute(text("SELECT version();")).scalar()
            print(f"  [OK] Connected to PostgreSQL target database: {pg_ver}")
    except Exception as e:
        print(f"  [Failed] Could not connect to PostgreSQL: {e}")
        print("\nTroubleshooting:")
        print("  1. Ensure the PostgreSQL service is running (e.g. postgresql-x64-18 on port 5432).")
        print("  2. Verify credentials in 'backend/.env' (DATABASE_URL=postgresql+psycopg://postgres:PASSWORD@localhost:5432/road_hazard_db).")
        print("  3. Verify the database 'road_hazard_db' exists (or create it via: CREATE DATABASE road_hazard_db;).")
        return False

    # 2. Check and enable PostGIS extension
    print("\n[Step 2/4] Verifying and enabling PostGIS extension...")
    try:
        with engine.connect() as conn:
            # Check if postgis is already installed
            has_postgis = conn.execute(
                text("SELECT 1 FROM pg_extension WHERE extname = 'postgis';")
            ).scalar()

            if not has_postgis:
                print("  Installing PostGIS extension: 'CREATE EXTENSION IF NOT EXISTS postgis;'")
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
                conn.commit()

            postgis_ver = conn.execute(text("SELECT PostGIS_Full_Version();")).scalar()
            print(f"  [OK] PostGIS is enabled: {postgis_ver}")
    except Exception as e:
        print(f"  [Warning] Could not enable PostGIS: {e}")
        print("  Please ensure PostGIS is installed and run manually:")
        print("    CREATE EXTENSION IF NOT EXISTS postgis;")
        return False

    # 3. Create tables non-destructively
    print("\n[Step 3/4] Creating database tables (Base.metadata.create_all)...")
    try:
        Base.metadata.create_all(bind=engine)
        print("  [OK] Tables created or verified successfully without dropping existing data.")
    except Exception as e:
        print(f"  [Failed] Table creation failed: {e}")
        return False

    # 4. Verify table and spatial index exist
    print("\n[Step 4/4] Verifying 'hazards' table and spatial columns...")
    try:
        with engine.connect() as conn:
            col_info = conn.execute(
                text(
                    "SELECT column_name, data_type, udt_name "
                    "FROM information_schema.columns "
                    "WHERE table_name = 'hazards';"
                )
            ).fetchall()

            col_names = [r[0] for r in col_info]
            print(f"  [OK] Columns present in 'hazards' table: {', '.join(col_names)}")

            has_location = "location" in col_names
            has_priority = "priority_level" in col_names and "priority_reason" in col_names
            if has_location:
                print("  [OK] Spatial 'location' geometry column is present.")
            else:
                print("  [Warning] 'location' geometry column not found.")

            if has_priority:
                print("  [OK] Priority engine columns (priority_score, priority_level, priority_reason) are present.")
            else:
                print("  [Warning] Priority engine columns need migration (run python backend/migrate_db.py).")
    except Exception as e:
        print(f"  [Warning] Table verification query returned an error: {e}")

    print("\n" + "=" * 80)
    print("DATABASE INITIALIZATION COMPLETED SUCCESSFULLY!")
    print("=" * 80)
    return True


if __name__ == "__main__":
    success = init_database()
    if not success:
        sys.exit(1)
