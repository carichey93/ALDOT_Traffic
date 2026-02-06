"""
Fetches traffic event data from ALDOT's AlgoTraffic API and stores in the database.
"""

from datetime import datetime
from typing import Optional

import requests

from app.config import API_BASE, EVENT_TYPES
from data.database import init_db, upsert_events


def process_lane_info(lane_info: list) -> str:
    """
    Process lane information from the API response.
    Returns a comma-separated string of closed lanes.
    """
    if not lane_info:
        return ""

    closed_lanes = []
    through_lane_names = {
        0: "Through Lane",
        1: "Inside Lane",
        2: "Center Lane",
        3: "Outside Lane",
    }

    for direction_info in lane_info:
        direction = direction_info.get("direction", "")
        for lane in direction_info.get("lanes", []):
            if lane.get("state") == "Closed":
                lane_type = lane.get("type", "")
                placement = lane.get("placement", 0)

                if lane_type == "ThroughLane":
                    lane_type = through_lane_names.get(placement, "Through Lane")
                elif lane_type == "RightShoulder":
                    lane_type = "Right Shoulder"
                elif lane_type == "LeftShoulder":
                    lane_type = "Left Shoulder"
                elif lane_type == "TurnLane":
                    lane_type = "Turn Lane"

                closed_lanes.append(f"{direction} {lane_type}")

    return ", ".join(closed_lanes)


def parse_datetime(dt_string: Optional[str]) -> Optional[str]:
    """Parse ISO datetime string to consistent format."""
    if not dt_string:
        return None
    try:
        dt_string = dt_string.replace("Z", "+00:00")
        dt = datetime.fromisoformat(dt_string)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return None


def get_api_response(session: requests.Session, url: str) -> list[dict]:
    """Fetch data from the API and return event dicts ready for database insertion."""
    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()

        events = []
        for event in data:
            start_loc = event.get("startLocation") or {}
            end_loc = event.get("endLocation") or {}

            lat = start_loc.get("latitude")
            lon = start_loc.get("longitude")
            if not lat or not lon:
                continue

            severity = event.get("severity") or ""
            severity = severity.replace("Delay", "").strip()

            events.append(
                {
                    "event_id": event.get("id"),
                    "category": event.get("type"),
                    "title": event.get("title"),
                    "location": event.get("shortSubTitle"),
                    "full_location": event.get("subTitle"),
                    "description": event.get("description"),
                    "region": event.get("responsibleRegion"),
                    "severity": severity,
                    "county": start_loc.get("county"),
                    "city": start_loc.get("city"),
                    "road": start_loc.get("routeDesignator"),
                    "road_display": start_loc.get("displayRouteDesignator"),
                    "road_type": start_loc.get("routeDesignatorType"),
                    "cross_street": start_loc.get("displayCrossStreet"),
                    "direction": start_loc.get("direction"),
                    "mile_marker": start_loc.get("linearReference"),
                    "start_time": parse_datetime(event.get("start")),
                    "end_time": parse_datetime(event.get("end")),
                    "last_updated": parse_datetime(event.get("lastUpdatedAt")),
                    "active": 1 if event.get("active") else 0,
                    "start_latitude": lat,
                    "start_longitude": lon,
                    "end_latitude": end_loc.get("latitude"),
                    "end_longitude": end_loc.get("longitude"),
                    "lane_closures": process_lane_info(
                        event.get("laneDirections", [])
                    ),
                }
            )

        return events

    except requests.RequestException as e:
        print(f"Request failed for {url}: {e}")
        return []
    except ValueError as e:
        print(f"JSON parsing failed for {url}: {e}")
        return []


def update_events() -> int:
    """
    Fetch traffic event data from all API endpoints and update the database.
    Returns the number of events processed.
    """
    init_db()

    all_events = []

    with requests.Session() as session:
        session.headers.update(
            {
                "User-Agent": "ALDOT-Traffic-Dashboard/1.0",
                "Accept": "application/json",
            }
        )

        for event_type in EVENT_TYPES:
            url = f"{API_BASE}?type={event_type}"
            events = get_api_response(session, url)
            all_events.extend(events)
            print(f"Fetched {len(events)} {event_type} events")

    if all_events:
        upsert_events(all_events)
        print(f"Total: {len(all_events)} events updated in database")

    return len(all_events)
