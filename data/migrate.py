"""
One-time migration script to load existing CSV data into the SQLite database.

Usage:
    python -m data.migrate
"""

import os
import sys
from pathlib import Path

# Allow running as a standalone script or as a module
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import DB_FILE
from data.database import get_event_count, init_db, migrate_from_csv

CSV_FILE = Path(__file__).parent.parent / "traffic_events.csv"


def main():
    print("=" * 60)
    print("ALDOT Traffic Events - CSV to SQLite Migration")
    print("=" * 60)

    if not CSV_FILE.exists():
        print(f"ERROR: CSV file not found: {CSV_FILE}")
        sys.exit(1)

    csv_size = os.path.getsize(CSV_FILE) / (1024 * 1024)
    print(f"Source CSV: {CSV_FILE}")
    print(f"CSV Size: {csv_size:.2f} MB")

    if DB_FILE.exists():
        existing_count = get_event_count()
        print(f"Database already exists with {existing_count:,} records.")
        response = input(
            "Do you want to re-migrate? This will update existing records. (y/N): "
        )
        if response.lower() != "y":
            print("Migration cancelled.")
            return

    print("\nInitializing database...")
    init_db()

    print("Starting migration...")
    count = migrate_from_csv(str(CSV_FILE))

    print("\n" + "=" * 60)
    print("Migration Complete!")
    print("=" * 60)
    print(f"Records migrated: {count:,}")

    db_size = os.path.getsize(DB_FILE) / (1024 * 1024)
    print(f"Database size: {db_size:.2f} MB")
    print(f"Database location: {DB_FILE}")


if __name__ == "__main__":
    main()
