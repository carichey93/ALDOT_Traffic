"""
Database layer for ALDOT Traffic Events.
Uses SQLite for efficient storage and querying of traffic event data.
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

DB_FILE = Path(__file__).parent / "traffic_events.db"


@contextmanager
def get_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Initialize the database schema and indexes."""
    with get_connection() as conn:
        # Check if we need to migrate (add new columns)
        cursor = conn.execute("PRAGMA table_info(traffic_events)")
        existing_columns = {row[1] for row in cursor.fetchall()}

        if not existing_columns:
            # Create new table with all columns
            conn.execute("""
                CREATE TABLE IF NOT EXISTS traffic_events (
                    event_id INTEGER PRIMARY KEY,
                    category TEXT NOT NULL,
                    title TEXT,
                    location TEXT,
                    full_location TEXT,
                    description TEXT,
                    region TEXT,
                    severity TEXT,
                    county TEXT,
                    city TEXT,
                    road TEXT,
                    road_display TEXT,
                    road_type TEXT,
                    cross_street TEXT,
                    direction TEXT,
                    mile_marker REAL,
                    start_time DATETIME NOT NULL,
                    end_time DATETIME,
                    last_updated DATETIME,
                    active INTEGER,
                    start_latitude REAL NOT NULL,
                    start_longitude REAL NOT NULL,
                    end_latitude REAL,
                    end_longitude REAL,
                    lane_closures TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
        else:
            # Add new columns if they don't exist
            new_columns = [
                ("full_location", "TEXT"),
                ("road_display", "TEXT"),
                ("cross_street", "TEXT"),
                ("direction", "TEXT"),
                ("mile_marker", "REAL"),
                ("last_updated", "DATETIME"),
                ("active", "INTEGER"),
            ]
            for col_name, col_type in new_columns:
                if col_name not in existing_columns:
                    conn.execute(f"ALTER TABLE traffic_events ADD COLUMN {col_name} {col_type}")

        # Create indexes for common query patterns
        conn.execute("CREATE INDEX IF NOT EXISTS idx_start_time ON traffic_events(start_time)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_county ON traffic_events(county)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON traffic_events(category)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_severity ON traffic_events(severity)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_county_category ON traffic_events(county, category)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_coords ON traffic_events(start_latitude, start_longitude)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_active ON traffic_events(active)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_road ON traffic_events(road)")

        conn.commit()


def upsert_events(events: list[dict]):
    """
    Insert or update multiple events in the database.
    Uses INSERT OR REPLACE for efficient upserts.
    """
    if not events:
        return 0

    with get_connection() as conn:
        cursor = conn.executemany("""
            INSERT OR REPLACE INTO traffic_events (
                event_id, category, title, location, full_location, description, region,
                severity, county, city, road, road_display, road_type, cross_street,
                direction, mile_marker, start_time, end_time, last_updated, active,
                start_latitude, start_longitude, end_latitude, end_longitude, lane_closures
            ) VALUES (
                :event_id, :category, :title, :location, :full_location, :description, :region,
                :severity, :county, :city, :road, :road_display, :road_type, :cross_street,
                :direction, :mile_marker, :start_time, :end_time, :last_updated, :active,
                :start_latitude, :start_longitude, :end_latitude, :end_longitude, :lane_closures
            )
        """, events)
        conn.commit()
        return cursor.rowcount


def query_events(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    counties: Optional[list[str]] = None,
    categories: Optional[list[str]] = None,
    severities: Optional[list[str]] = None,
    active_only: bool = False,
) -> pd.DataFrame:
    """
    Query events with optional filters.
    Returns a pandas DataFrame for compatibility with existing visualization code.
    """
    conditions = ["start_latitude IS NOT NULL", "start_longitude IS NOT NULL"]
    params = []

    if start_date:
        conditions.append("date(start_time) >= date(?)")
        params.append(start_date)

    if end_date:
        conditions.append("date(start_time) <= date(?)")
        params.append(end_date)

    if counties and "All" not in counties:
        placeholders = ",".join("?" * len(counties))
        conditions.append(f"county IN ({placeholders})")
        params.extend(counties)

    if categories and "All" not in categories:
        placeholders = ",".join("?" * len(categories))
        conditions.append(f"category IN ({placeholders})")
        params.extend(categories)

    if severities and "All" not in severities:
        placeholders = ",".join("?" * len(severities))
        conditions.append(f"severity IN ({placeholders})")
        params.extend(severities)

    if active_only:
        conditions.append("active = 1")

    where_clause = " AND ".join(conditions)

    query = f"""
        SELECT
            event_id as "Event ID",
            category as "Category",
            title as "Title",
            location as "Location",
            full_location as "Full Location",
            description as "Description",
            region as "Region",
            severity as "Severity",
            county as "County",
            city as "City",
            road as "Road",
            road_display as "Road Display",
            road_type as "Road Type",
            cross_street as "Cross Street",
            direction as "Direction",
            mile_marker as "Mile Marker",
            start_time as "Start Time",
            end_time as "End Time",
            last_updated as "Last Updated",
            active as "Active",
            start_latitude as "Start Latitude",
            start_longitude as "Start Longitude",
            end_latitude as "End Latitude",
            end_longitude as "End Longitude",
            lane_closures as "Lane Closures"
        FROM traffic_events
        WHERE {where_clause}
        ORDER BY start_time DESC
    """

    with get_connection() as conn:
        df = pd.read_sql_query(query, conn, params=params, parse_dates=["Start Time", "End Time", "Last Updated"])

    return df


def get_unique_values(column: str) -> list:
    """Get unique non-null values for a column (for filter dropdowns)."""
    column_map = {
        "County": "county",
        "Category": "category",
        "Severity": "severity",
        "Region": "region",
        "Road": "road",
        "Direction": "direction",
    }
    db_column = column_map.get(column, column.lower())

    with get_connection() as conn:
        cursor = conn.execute(f"""
            SELECT DISTINCT {db_column}
            FROM traffic_events
            WHERE {db_column} IS NOT NULL AND {db_column} != ''
            ORDER BY {db_column}
        """)
        return [row[0] for row in cursor.fetchall()]


def get_date_range() -> tuple[datetime, datetime]:
    """Get the min and max start_time in the database."""
    with get_connection() as conn:
        cursor = conn.execute("""
            SELECT MIN(start_time), MAX(start_time) FROM traffic_events
        """)
        row = cursor.fetchone()
        min_date = datetime.fromisoformat(row[0]) if row[0] else datetime.now()
        max_date = datetime.fromisoformat(row[1]) if row[1] else datetime.now()
        return min_date, max_date


def get_event_count() -> int:
    """Get total number of events in the database."""
    with get_connection() as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM traffic_events")
        return cursor.fetchone()[0]


def get_last_update_time() -> Optional[datetime]:
    """Get the most recent created_at timestamp."""
    with get_connection() as conn:
        cursor = conn.execute("""
            SELECT MAX(created_at) FROM traffic_events
        """)
        row = cursor.fetchone()
        if row[0]:
            return datetime.fromisoformat(row[0])
        return None


def migrate_from_csv(csv_path: str, batch_size: int = 5000) -> int:
    """
    Migrate data from CSV file to database.
    Processes in batches to handle large files efficiently.
    Returns the number of records migrated.
    """
    init_db()

    df = pd.read_csv(csv_path)
    df["Start Time"] = pd.to_datetime(df["Start Time"])
    df["End Time"] = pd.to_datetime(df["End Time"])

    # Drop rows without coordinates
    df = df.dropna(subset=["Start Latitude", "Start Longitude"])

    total_inserted = 0

    for i in range(0, len(df), batch_size):
        batch = df.iloc[i:i + batch_size]
        events = []

        for _, row in batch.iterrows():
            events.append({
                "event_id": int(row["Event ID"]),
                "category": row.get("Category"),
                "title": row.get("Title"),
                "location": row.get("Location"),
                "full_location": None,  # Not in old CSV
                "description": row.get("Description"),
                "region": row.get("Region"),
                "severity": row.get("Severity"),
                "county": row.get("County"),
                "city": row.get("City"),
                "road": row.get("Road"),
                "road_display": None,  # Not in old CSV
                "road_type": row.get("Road Type"),
                "cross_street": None,  # Not in old CSV
                "direction": None,  # Not in old CSV
                "mile_marker": None,  # Not in old CSV
                "start_time": row["Start Time"].isoformat() if pd.notna(row["Start Time"]) else None,
                "end_time": row["End Time"].isoformat() if pd.notna(row.get("End Time")) else None,
                "last_updated": None,  # Not in old CSV
                "active": None,  # Not in old CSV
                "start_latitude": row["Start Latitude"],
                "start_longitude": row["Start Longitude"],
                "end_latitude": row.get("End Latitude") if pd.notna(row.get("End Latitude")) else None,
                "end_longitude": row.get("End Longitude") if pd.notna(row.get("End Longitude")) else None,
                "lane_closures": row.get("Lane Closures"),
            })

        upsert_events(events)
        total_inserted += len(events)
        print(f"Migrated {total_inserted:,} records...")

    return total_inserted


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_FILE}")
