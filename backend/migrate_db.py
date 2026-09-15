#!/usr/bin/env python3
"""
Road Hazard Detection - Database Migration Script.
Safely adds priority_level and priority_reason columns, converts priority_score to Float,
and backfills existing records without dropping tables or losing data.
"""

import sys
from pathlib import Path
from sqlalchemy import text

# Add project root directory to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.database import engine
from backend.services.priority import calculate_priority_score


def run_migration():
    print("=" * 80)
    print("ROAD HAZARD DATABASE MIGRATION (Severity & Priority Engine)")
    print("=" * 80)

    if engine is None:
        print("[Error] SQLAlchemy engine is not configured.")
        return False

    try:
        with engine.connect() as conn:
            # 1. Check if table hazards exists
            tbl_exists = conn.execute(
                text("SELECT 1 FROM information_schema.tables WHERE table_name = 'hazards';")
            ).scalar()

            if not tbl_exists:
                print("Table 'hazards' does not exist yet. Run backend/init_db.py first.")
                return True

            print("[Step 1/3] Applying non-destructive column alterations...")
            # Alter priority_score to float / double precision
            conn.execute(
                text("ALTER TABLE hazards ALTER COLUMN priority_score TYPE DOUBLE PRECISION USING priority_score::double precision;")
            )
            # Add priority_level column if not present
            conn.execute(
                text("ALTER TABLE hazards ADD COLUMN IF NOT EXISTS priority_level VARCHAR(20) DEFAULT 'Medium';")
            )
            # Add priority_reason column if not present
            conn.execute(
                text("ALTER TABLE hazards ADD COLUMN IF NOT EXISTS priority_reason VARCHAR(255);")
            )
            # Add index on priority_level
            conn.execute(
                text("CREATE INDEX IF NOT EXISTS ix_hazards_priority_level ON hazards (priority_level);")
            )
            conn.commit()
            print("  [OK] Columns 'priority_level' and 'priority_reason' verified/added.")

            # 2. Backfill existing records
            print("\n[Step 2/3] Backfilling priority scores and reasons for existing records...")
            records = conn.execute(
                text("SELECT id, hazard_type, severity, confidence, latitude, longitude, priority_score, priority_reason FROM hazards;")
            ).fetchall()

            updated_count = 0
            for row in records:
                hid, htype, sev, conf, lat, lon, p_score, p_reason = row
                # If priority_score was on the old 1-3 scale or reason is missing, recalculate
                if p_reason is None or (p_score is not None and p_score <= 5.0):
                    new_score, new_level, new_reason = calculate_priority_score(
                        hazard_type=htype,
                        severity=sev or "Medium",
                        confidence=conf or 0.80,
                        latitude=lat,
                        longitude=lon,
                    )
                    conn.execute(
                        text(
                            "UPDATE hazards SET priority_score = :ps, priority_level = :pl, priority_reason = :pr WHERE id = :id;"
                        ),
                        {"ps": new_score, "pl": new_level, "pr": new_reason, "id": hid},
                    )
                    updated_count += 1

            conn.commit()
            print(f"  [OK] Backfilled {updated_count} existing hazard records.")

            # 3. Verify columns
            print("\n[Step 3/3] Verifying table structure...")
            cols = conn.execute(
                text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'hazards';")
            ).fetchall()
            col_dict = {r[0]: r[1] for r in cols}
            print(f"  priority_score type: {col_dict.get('priority_score')}")
            print(f"  priority_level type: {col_dict.get('priority_level')}")
            print(f"  priority_reason type: {col_dict.get('priority_reason')}")

        print("\n" + "=" * 80)
        print("DATABASE MIGRATION COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        return True

    except Exception as e:
        print(f"[Migration Failed] Error: {e}")
        return False


if __name__ == "__main__":
    success = run_migration()
    if not success:
        sys.exit(1)
