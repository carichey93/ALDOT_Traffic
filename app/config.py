"""
Application constants and configuration.
"""

from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
GEOJSON_FILE = PROJECT_ROOT / "Alabama_Counties.geojson"
LOGO_FILE = PROJECT_ROOT / "website_logo.png"
STATIC_DIR = PROJECT_ROOT / "static"
DB_FILE = PROJECT_ROOT / "traffic_events.db"

# API
API_BASE = "https://api.algotraffic.com/v3.0/TrafficEvents"
EVENT_TYPES = ["Roadwork", "Crash", "Incident", "RoadCondition"]

# Scoring weights
SEVERITY_WEIGHTS = {"Major": 3, "Moderate": 2, "Minor": 1}

# Severity color maps
SEVERITY_COLORS = {
    "Major": "#ff4444",
    "Moderate": "#ffaa00",
    "Minor": "#4488ff",
    "Closed": "#333333",
}

SEVERITY_MAP_COLORS = {
    "Major": "red",
    "Moderate": "orange",
    "Minor": "blue",
}

# Clearance time bounds (minutes)
MIN_CLEARANCE_MINUTES = 1
MAX_CLEARANCE_MINUTES = 1440  # 24 hours

# Clustering
DEFAULT_CLUSTER_RADIUS_MILES = 0.5
MIN_CLUSTER_SIZE = 3

# Work zone proximity (miles)
WORK_ZONE_BUFFER_MILES = 2

# Data refresh interval (seconds)
DATA_REFRESH_INTERVAL = 1800  # 30 minutes

# Page config
PAGE_TITLE = "Rammer Slammer Traffic Jammer"
PAGE_ICON = "static/apple-touch-icon.png"

# Custom CSS
CUSTOM_CSS = """
<style>
    .danger-high { color: #ff4444; font-weight: bold; }
    .danger-medium { color: #ffaa00; font-weight: bold; }
    .danger-low { color: #44aa44; }
    .stMetric > div { background-color: #f0f2f6; border-radius: 10px; padding: 10px; }
</style>
"""

# Apple touch icon HTML
APPLE_TOUCH_ICON_HTML = """
<link rel="apple-touch-icon" href="./static/apple-touch-icon.png">
<link rel="apple-touch-icon" sizes="180x180" href="./static/apple-touch-icon.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Traffic Jammer">
"""
