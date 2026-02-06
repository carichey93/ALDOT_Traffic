"""
Business logic and calculations for crash analytics.

Provides danger scoring, clearance time calculations, geographic clustering,
and work zone proximity analysis.
"""

import numpy as np
import pandas as pd

from app.config import (
    DEFAULT_CLUSTER_RADIUS_MILES,
    MAX_CLEARANCE_MINUTES,
    MIN_CLEARANCE_MINUTES,
    MIN_CLUSTER_SIZE,
    SEVERITY_WEIGHTS,
)


def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two lat/lon points in miles."""
    R = 3959  # Earth's radius in miles
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c


def calculate_danger_score(severity_series: pd.Series) -> int:
    """Calculate danger score from a Series of severity values."""
    score = 0
    for severity, weight in SEVERITY_WEIGHTS.items():
        score += (severity_series == severity).sum() * weight
    return score


def calculate_avg_clearance_minutes(crashes: pd.DataFrame) -> float | None:
    """Calculate average clearance time in minutes. Returns None if not calculable."""
    if crashes is None or crashes.empty:
        return None

    crashes_with_times = crashes.dropna(subset=["Start Time", "End Time"])
    if crashes_with_times.empty:
        return None

    try:
        start_times = pd.to_datetime(crashes_with_times["Start Time"])
        end_times = pd.to_datetime(crashes_with_times["End Time"])
        durations = (end_times - start_times).dt.total_seconds() / 60

        valid_durations = durations[
            (durations > MIN_CLEARANCE_MINUTES) & (durations < MAX_CLEARANCE_MINUTES)
        ]
        if valid_durations.empty:
            return None

        return valid_durations.mean()
    except Exception:
        return None


def calculate_avg_clearance_time(crashes: pd.DataFrame) -> str:
    """Calculate average clearance time as a formatted string."""
    avg_minutes = calculate_avg_clearance_minutes(crashes)
    if avg_minutes is None:
        return "N/A"
    if avg_minutes < 60:
        return f"{avg_minutes:.0f} min"
    return f"{avg_minutes / 60:.1f} hrs"


def calculate_construction_zone_crashes(
    crashes: pd.DataFrame, roadwork: pd.DataFrame
) -> int:
    """
    Estimate crashes that occurred in active construction zones.

    A crash is considered to be in a work zone if:
    1. It's on the same road AND county as an active roadwork project, AND
    2. If mile markers are available, the crash is within 2 miles of
       the roadwork location.
    """
    if roadwork.empty or crashes.empty:
        return 0

    construction_crashes = 0

    # Build a lookup of roadwork by road+county
    roadwork_by_location = {}
    for _, rw in roadwork.iterrows():
        road = rw.get("Road")
        county = rw.get("County")
        if pd.isna(road) or pd.isna(county):
            continue
        key = (road, county)
        if key not in roadwork_by_location:
            roadwork_by_location[key] = []
        roadwork_by_location[key].append({"start_mm": rw.get("Mile Marker")})

    for _, crash in crashes.iterrows():
        crash_road = crash.get("Road")
        crash_county = crash.get("County")
        crash_mm = crash.get("Mile Marker")

        if pd.isna(crash_road) or pd.isna(crash_county):
            continue

        key = (crash_road, crash_county)
        if key not in roadwork_by_location:
            continue

        if pd.notna(crash_mm):
            for rw in roadwork_by_location[key]:
                rw_mm = rw["start_mm"]
                if pd.notna(rw_mm):
                    if abs(crash_mm - rw_mm) <= 2:
                        construction_crashes += 1
                        break
            else:
                construction_crashes += 1
        else:
            construction_crashes += 1

    return construction_crashes


def find_crash_clusters(
    crashes: pd.DataFrame,
    radius_miles: float = DEFAULT_CLUSTER_RADIUS_MILES,
) -> pd.DataFrame:
    """
    Group crashes within radius_miles of each other into clusters.

    Returns a DataFrame of clusters with columns:
    Crashes, Lat, Lon, Location, Road, County.
    """
    crashes_with_coords = crashes.dropna(
        subset=["Start Latitude", "Start Longitude"]
    ).copy()

    if crashes_with_coords.empty:
        return pd.DataFrame()

    crashes_with_coords["cluster_id"] = -1
    cluster_id = 0

    coords = crashes_with_coords[["Start Latitude", "Start Longitude"]].values
    n = len(coords)
    assigned = set()

    for i in range(n):
        if i in assigned:
            continue

        cluster_points = [i]
        assigned.add(i)

        for j in range(i + 1, n):
            if j in assigned:
                continue
            dist = haversine_distance(
                coords[i][0], coords[i][1], coords[j][0], coords[j][1]
            )
            if dist <= radius_miles:
                cluster_points.append(j)
                assigned.add(j)

        if len(cluster_points) >= MIN_CLUSTER_SIZE:
            for idx in cluster_points:
                crashes_with_coords.iloc[
                    idx, crashes_with_coords.columns.get_loc("cluster_id")
                ] = cluster_id
            cluster_id += 1

    clustered = crashes_with_coords[crashes_with_coords["cluster_id"] >= 0]

    if clustered.empty:
        return pd.DataFrame()

    cluster_stats = (
        clustered.groupby("cluster_id")
        .agg(
            {
                "Event ID": "count",
                "Start Latitude": "mean",
                "Start Longitude": "mean",
                "Location": "first",
                "Road": "first",
                "County": "first",
            }
        )
        .rename(
            columns={
                "Event ID": "Crashes",
                "Start Latitude": "Lat",
                "Start Longitude": "Lon",
            }
        )
    )

    return cluster_stats.sort_values("Crashes", ascending=False)
