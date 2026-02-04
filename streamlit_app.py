"""
Alabama Crash Analytics Dashboard
"""

import datetime
from datetime import datetime as dt
from pathlib import Path

import folium
import folium.plugins as plugins
import geopandas as gpd
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit_folium as stf

from database import (
    get_date_range,
    get_last_update_time,
    get_unique_values,
    init_db,
    query_events,
)

GEOJSON_FILE = Path(__file__).parent / "Alabama_Counties.geojson"

st.set_page_config(
    page_title="Rammer Slammer Traffic Jammer",
    page_icon="static/apple-touch-icon.png",
    layout="wide",
)

# Add Apple touch icon for iOS home screen
st.markdown("""
<link rel="apple-touch-icon" href="./static/apple-touch-icon.png">
<link rel="apple-touch-icon" sizes="180x180" href="./static/apple-touch-icon.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Traffic Jammer">
""", unsafe_allow_html=True)

# Custom CSS for better styling
st.markdown("""
<style>
    .danger-high { color: #ff4444; font-weight: bold; }
    .danger-medium { color: #ffaa00; font-weight: bold; }
    .danger-low { color: #44aa44; }
    .stMetric > div { background-color: #f0f2f6; border-radius: 10px; padding: 10px; }
</style>
""", unsafe_allow_html=True)


def main():
    init_db()

    # Display logo and title
    col_logo, col_title = st.columns([1, 4])
    with col_logo:
        st.image("website_logo.png", width=100)
    with col_title:
        st.title("Rammer Slammer Traffic Jammer")

    # Sidebar
    with st.sidebar:
        st.header("Dashboard Controls")

        # Date range selection
        date_range = st.selectbox(
            "Time Period",
            ["Today", "Last 7 Days", "Last 30 Days", "This Year", "All Time"],
            index=2
        )

        start_date, end_date, period_label = get_date_range_from_selection(date_range)
        prev_start, prev_end = get_previous_period(start_date, end_date, date_range)

        # County filter
        counties = get_unique_values("County")
        selected_counties = st.multiselect(
            "Filter by County",
            ["All"] + sorted(counties),
            default=["All"]
        )

        # Severity filter
        selected_severities = st.multiselect(
            "Severity",
            ["All", "Major", "Moderate", "Minor"],
            default=["All"]
        )

        st.divider()
        st.caption(f"Last updated: {get_last_update_time().strftime('%Y-%m-%d %H:%M') if get_last_update_time() else 'Never'}")

    # Load crash data for current period
    crashes = query_events(
        start_date=start_date,
        end_date=end_date,
        counties=selected_counties if "All" not in selected_counties else None,
        categories=["Crash"],
        severities=selected_severities if "All" not in selected_severities else None,
    )

    # Load crash data for previous period (for comparison)
    prev_crashes = query_events(
        start_date=prev_start,
        end_date=prev_end,
        counties=selected_counties if "All" not in selected_counties else None,
        categories=["Crash"],
        severities=selected_severities if "All" not in selected_severities else None,
    )

    # Load roadwork for construction zone analysis
    roadwork = query_events(
        start_date=start_date,
        end_date=end_date,
        categories=["Roadwork"],
    )

    if crashes.empty:
        st.warning("No crash data found for the selected filters.")
        return

    # Main dashboard tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Overview",
        "Danger Rankings",
        "Time Analysis",
        "Crash Map",
        "Data Explorer"
    ])

    with tab1:
        display_overview(crashes, prev_crashes, roadwork, start_date, end_date, period_label)

    with tab2:
        display_danger_rankings(crashes)

    with tab3:
        display_time_analysis(crashes)

    with tab4:
        display_crash_map(crashes, roadwork)

    with tab5:
        display_data_explorer(crashes)


def get_date_range_from_selection(selection: str) -> tuple:
    """Convert selection to date range and period label."""
    today = datetime.date.today()

    ranges = {
        "Today": (today, today, "yesterday"),
        "Last 7 Days": (today - datetime.timedelta(days=7), today, "prior 7 days"),
        "Last 30 Days": (today - datetime.timedelta(days=30), today, "prior 30 days"),
        "This Year": (datetime.date(today.year, 1, 1), today, "same period last year"),
        "All Time": (datetime.date(2019, 1, 1), today, None),
    }
    return ranges.get(selection, (today, today, None))


def get_previous_period(start_date, end_date, selection: str) -> tuple:
    """Get the previous period for comparison."""
    if selection == "All Time":
        return None, None

    days_in_period = (end_date - start_date).days + 1

    if selection == "This Year":
        # Compare to same period last year
        prev_end = end_date.replace(year=end_date.year - 1)
        prev_start = start_date.replace(year=start_date.year - 1)
    else:
        # Compare to previous equivalent period
        prev_end = start_date - datetime.timedelta(days=1)
        prev_start = prev_end - datetime.timedelta(days=days_in_period - 1)

    return prev_start, prev_end


@st.cache_data(ttl=300)
def load_geojson():
    """Load and cache the GeoJSON file."""
    return gpd.read_file(GEOJSON_FILE)


def display_overview(crashes: pd.DataFrame, prev_crashes: pd.DataFrame, roadwork: pd.DataFrame,
                     start_date, end_date, period_label: str):
    """Display overview metrics and insights."""

    # Calculate key metrics
    total_crashes = len(crashes)
    prev_total = len(prev_crashes) if prev_crashes is not None and not prev_crashes.empty else 0
    major_crashes = len(crashes[crashes["Severity"] == "Major"])
    prev_major = len(prev_crashes[prev_crashes["Severity"] == "Major"]) if prev_crashes is not None and not prev_crashes.empty else 0
    moderate_crashes = len(crashes[crashes["Severity"] == "Moderate"])
    prev_moderate = len(prev_crashes[prev_crashes["Severity"] == "Moderate"]) if prev_crashes is not None and not prev_crashes.empty else 0

    # Calculate crashes in construction zones
    construction_crashes = calculate_construction_zone_crashes(crashes, roadwork)

    # Calculate average clearance time
    avg_clearance = calculate_avg_clearance_time(crashes)

    # Calculate percentage changes
    def pct_change(current, previous, label):
        if previous == 0 or label is None:
            return None, None
        pct = ((current - previous) / previous) * 100
        # Use +/- prefix so Streamlit shows correct arrow direction
        if pct > 0:
            return f"+{pct:.1f}% from {label}", pct
        else:
            return f"{pct:.1f}% from {label}", pct

    # Top metrics row
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        delta, _ = pct_change(total_crashes, prev_total, period_label)
        st.metric("Total Crashes", f"{total_crashes:,}", delta=delta, delta_color="inverse")
    with col2:
        delta, _ = pct_change(major_crashes, prev_major, period_label)
        st.metric("Major", f"{major_crashes:,}", delta=delta, delta_color="inverse")
    with col3:
        delta, _ = pct_change(moderate_crashes, prev_moderate, period_label)
        st.metric("Moderate", f"{moderate_crashes:,}", delta=delta, delta_color="inverse")
    with col4:
        pct_in_workzone = f"{100*construction_crashes/total_crashes:.1f}% of total" if total_crashes else "0%"
        st.metric("In/Near Work Zones", f"{construction_crashes:,}", delta=pct_in_workzone, delta_color="off")
    with col5:
        st.metric("Avg Clearance", avg_clearance)

    st.divider()

    # Two column layout for charts
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Crashes by Severity")
        severity_counts = crashes["Severity"].value_counts()
        fig = px.pie(
            values=severity_counts.values,
            names=severity_counts.index,
            color=severity_counts.index,
            color_discrete_map={"Major": "#ff4444", "Moderate": "#ffaa00", "Minor": "#4488ff", "Closed": "#333333"},
            hole=0.4
        )
        fig.update_layout(margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig, width="stretch")

    with col2:
        st.subheader("Daily Crash Trend")
        crashes_copy = crashes.copy()
        crashes_copy["Date"] = pd.to_datetime(crashes_copy["Start Time"]).dt.date
        daily_counts = crashes_copy.groupby("Date").size().reset_index(name="Crashes")
        fig = px.area(daily_counts, x="Date", y="Crashes",
                      color_discrete_sequence=["#667eea"])
        fig.update_layout(margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig, width="stretch")

    # Insights section
    st.subheader("Quick Insights")
    col1, col2, col3, col4 = st.columns(4)

    crashes_copy["Start Time"] = pd.to_datetime(crashes_copy["Start Time"])
    crashes_copy["DayOfWeek"] = crashes_copy["Start Time"].dt.day_name()
    crashes_copy["Hour"] = crashes_copy["Start Time"].dt.hour

    with col1:
        # Worst specific date
        worst_date = crashes_copy["Date"].value_counts().idxmax()
        worst_date_count = crashes_copy["Date"].value_counts().max()
        worst_date_str = worst_date.strftime("%b %d, %Y") if hasattr(worst_date, 'strftime') else str(worst_date)
        st.info(f"**Worst Date:** {worst_date_str} ({worst_date_count:,} crashes)")

    with col2:
        # Worst day of week
        worst_day = crashes_copy["DayOfWeek"].value_counts().idxmax()
        worst_day_count = crashes_copy["DayOfWeek"].value_counts().max()
        st.info(f"**Worst Day of Week:** {worst_day} ({worst_day_count:,} crashes)")

    with col3:
        # Worst hour in AM/PM format
        worst_hour = int(crashes_copy["Hour"].value_counts().idxmax())
        worst_hour_count = crashes_copy["Hour"].value_counts().max()
        hour_ampm = datetime.datetime.strptime(f"{worst_hour}:00", "%H:%M").strftime("%I:%M %p").lstrip("0")
        st.info(f"**Worst Hour:** {hour_ampm} ({worst_hour_count:,} crashes)")

    with col4:
        # Most dangerous county
        worst_county = crashes["County"].value_counts().idxmax()
        worst_county_count = crashes["County"].value_counts().max()
        st.info(f"**Worst County:** {worst_county} ({worst_county_count:,} crashes)")


def calculate_construction_zone_crashes(crashes: pd.DataFrame, roadwork: pd.DataFrame) -> int:
    """
    Estimate crashes that occurred in active construction zones.

    Method: A crash is considered to be in a work zone if:
    1. It's on the same road AND county as an active roadwork project, AND
    2. If mile markers are available for both, the crash mile marker falls within
       the roadwork's start/end mile markers (with 1-mile buffer)

    This is an approximation since we don't have exact work zone boundaries.
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
        roadwork_by_location[key].append({
            "start_mm": rw.get("Mile Marker"),
            "end_mm": rw.get("End Latitude"),  # Note: end mile marker not available, using start only
        })

    for _, crash in crashes.iterrows():
        crash_road = crash.get("Road")
        crash_county = crash.get("County")
        crash_mm = crash.get("Mile Marker")

        if pd.isna(crash_road) or pd.isna(crash_county):
            continue

        key = (crash_road, crash_county)
        if key not in roadwork_by_location:
            continue

        # Found roadwork on same road/county
        # If we have mile markers, check if crash is within work zone
        if pd.notna(crash_mm):
            for rw in roadwork_by_location[key]:
                rw_mm = rw["start_mm"]
                if pd.notna(rw_mm):
                    # Consider within 2 miles of roadwork start as "in work zone"
                    if abs(crash_mm - rw_mm) <= 2:
                        construction_crashes += 1
                        break
            else:
                # No mile marker match, but same road/county - count it
                construction_crashes += 1
        else:
            # No crash mile marker, but same road/county - count it
            construction_crashes += 1

    return construction_crashes


def calculate_avg_clearance_time(crashes: pd.DataFrame) -> str:
    """Calculate average time to clear crashes."""
    crashes_with_times = crashes.dropna(subset=["Start Time", "End Time"])
    if crashes_with_times.empty:
        return "N/A"

    try:
        start_times = pd.to_datetime(crashes_with_times["Start Time"])
        end_times = pd.to_datetime(crashes_with_times["End Time"])
        durations = (end_times - start_times).dt.total_seconds() / 60  # minutes

        # Filter out unreasonable values (< 1 min or > 24 hours)
        valid_durations = durations[(durations > 1) & (durations < 1440)]
        if valid_durations.empty:
            return "N/A"

        avg_minutes = valid_durations.mean()
        if avg_minutes < 60:
            return f"{avg_minutes:.0f} min"
        else:
            return f"{avg_minutes/60:.1f} hrs"
    except Exception:
        return "N/A"


def calculate_danger_score(severity_series: pd.Series) -> int:
    """Calculate danger score: Major=3, Moderate=2, Minor=1."""
    score = 0
    score += (severity_series == "Major").sum() * 3
    score += (severity_series == "Moderate").sum() * 2
    score += (severity_series == "Minor").sum() * 1
    return score


def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in miles."""
    R = 3959  # Earth's radius in miles
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    return R * c


def find_crash_clusters(crashes: pd.DataFrame, radius_miles: float = 0.5) -> pd.DataFrame:
    """Group crashes within radius_miles of each other into clusters."""
    crashes_with_coords = crashes.dropna(subset=["Start Latitude", "Start Longitude"]).copy()

    if crashes_with_coords.empty:
        return pd.DataFrame()

    # Assign cluster IDs
    crashes_with_coords["cluster_id"] = -1
    cluster_id = 0

    coords = crashes_with_coords[["Start Latitude", "Start Longitude"]].values
    n = len(coords)
    assigned = set()

    for i in range(n):
        if i in assigned:
            continue

        # Start new cluster
        cluster_points = [i]
        assigned.add(i)

        for j in range(i + 1, n):
            if j in assigned:
                continue
            dist = haversine_distance(coords[i][0], coords[i][1], coords[j][0], coords[j][1])
            if dist <= radius_miles:
                cluster_points.append(j)
                assigned.add(j)

        # Only keep clusters with 3+ crashes
        if len(cluster_points) >= 3:
            for idx in cluster_points:
                crashes_with_coords.iloc[idx, crashes_with_coords.columns.get_loc("cluster_id")] = cluster_id
            cluster_id += 1

    # Filter to only clustered crashes
    clustered = crashes_with_coords[crashes_with_coords["cluster_id"] >= 0]

    if clustered.empty:
        return pd.DataFrame()

    # Aggregate by cluster
    cluster_stats = clustered.groupby("cluster_id").agg({
        "Event ID": "count",
        "Start Latitude": "mean",
        "Start Longitude": "mean",
        "Location": "first",
        "Road": "first",
        "County": "first"
    }).rename(columns={"Event ID": "Crashes", "Start Latitude": "Lat", "Start Longitude": "Lon"})

    cluster_stats = cluster_stats.sort_values("Crashes", ascending=False)

    return cluster_stats


def display_danger_rankings(crashes: pd.DataFrame):
    """Display danger rankings and leaderboards."""

    # Explanation of danger score
    st.caption("**Danger Score Calculation:** Major crashes = 3 points, Moderate = 2 points, Minor = 1 point")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Most Dangerous Roads")

        road_stats = crashes.groupby("Road").agg({
            "Event ID": "count",
            "Severity": [
                lambda x: (x == "Major").sum(),
                lambda x: (x == "Moderate").sum(),
                lambda x: (x == "Minor").sum()
            ]
        })
        road_stats.columns = ["Total", "Major", "Moderate", "Minor"]
        road_stats["Score"] = (road_stats["Major"] * 3) + (road_stats["Moderate"] * 2) + (road_stats["Minor"] * 1)
        road_stats = road_stats.sort_values("Score", ascending=False).head(15)

        fig = go.Figure(data=[go.Table(
            header=dict(
                values=["<b>Road</b>", "<b>Total</b>", "<b>Major</b>", "<b>Moderate</b>", "<b>Minor</b>", "<b>Score</b>"],
                fill_color='#667eea',
                font=dict(color='white', size=12),
                align='left'
            ),
            cells=dict(
                values=[
                    road_stats.index,
                    road_stats["Total"],
                    road_stats["Major"],
                    road_stats["Moderate"],
                    road_stats["Minor"],
                    road_stats["Score"]
                ],
                fill_color=[['#f0f2f6', '#ffffff'] * (len(road_stats) // 2 + 1)],
                align='left'
            )
        )])
        fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=400)
        st.plotly_chart(fig, width="stretch")

    with col2:
        st.subheader("Most Dangerous Counties")

        county_stats = crashes.groupby("County").agg({
            "Event ID": "count",
            "Severity": [
                lambda x: (x == "Major").sum(),
                lambda x: (x == "Moderate").sum(),
                lambda x: (x == "Minor").sum()
            ]
        })
        county_stats.columns = ["Total", "Major", "Moderate", "Minor"]
        county_stats["Score"] = (county_stats["Major"] * 3) + (county_stats["Moderate"] * 2) + (county_stats["Minor"] * 1)
        county_stats = county_stats.sort_values("Score", ascending=False).head(15)

        fig = go.Figure(data=[go.Table(
            header=dict(
                values=["<b>County</b>", "<b>Total</b>", "<b>Major</b>", "<b>Moderate</b>", "<b>Minor</b>", "<b>Score</b>"],
                fill_color='#764ba2',
                font=dict(color='white', size=12),
                align='left'
            ),
            cells=dict(
                values=[
                    county_stats.index,
                    county_stats["Total"],
                    county_stats["Major"],
                    county_stats["Moderate"],
                    county_stats["Minor"],
                    county_stats["Score"]
                ],
                fill_color=[['#f0f2f6', '#ffffff'] * (len(county_stats) // 2 + 1)],
                align='left'
            )
        )])
        fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=400)
        st.plotly_chart(fig, width="stretch")

    st.divider()

    # Hot spots - geographic clustering
    st.subheader("Crash Hot Spots")
    st.caption("Locations with 3+ crashes within 0.5 miles of each other")

    cluster_stats = find_crash_clusters(crashes, radius_miles=0.5)

    if not cluster_stats.empty:
        display_clusters = cluster_stats.reset_index(drop=True)[["Location", "Road", "County", "Crashes"]].head(20)
        st.dataframe(
            display_clusters,
            width="stretch",
            hide_index=True
        )
    else:
        st.info("No crash clusters found in this time period (requires 3+ crashes within 0.5 miles).")

    # Cross street analysis if available
    st.subheader("Dangerous Intersections")
    cross_street_crashes = crashes[crashes["Cross Street"].notna() & (crashes["Cross Street"] != "")]

    if not cross_street_crashes.empty:
        intersection_stats = cross_street_crashes.groupby(["Road", "Cross Street", "County"]).size().reset_index(name="Crashes")
        intersection_stats = intersection_stats.sort_values("Crashes", ascending=False).head(15)
        st.dataframe(intersection_stats, width="stretch", hide_index=True)
    else:
        st.info("No intersection data available.")


def display_time_analysis(crashes: pd.DataFrame):
    """Display time-based crash analysis."""

    crashes_copy = crashes.copy()
    crashes_copy["Start Time"] = pd.to_datetime(crashes_copy["Start Time"])
    crashes_copy["Hour"] = crashes_copy["Start Time"].dt.hour
    crashes_copy["DayOfWeek"] = crashes_copy["Start Time"].dt.dayofweek
    crashes_copy["DayName"] = crashes_copy["Start Time"].dt.day_name()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Crashes by Hour of Day")

        hourly = crashes_copy.groupby("Hour").size().reset_index(name="Crashes")
        # Create AM/PM labels
        hourly["Hour Label"] = hourly["Hour"].apply(
            lambda h: datetime.datetime.strptime(f"{int(h)}:00", "%H:%M").strftime("%I %p").lstrip("0")
        )
        fig = px.bar(hourly, x="Hour Label", y="Crashes",
                     color="Crashes",
                     color_continuous_scale="Reds")
        fig.update_layout(
            xaxis_title="Hour",
            margin=dict(t=20, b=20, l=20, r=20)
        )
        st.plotly_chart(fig, width="stretch")

        # Rush hour analysis
        morning_rush = len(crashes_copy[(crashes_copy["Hour"] >= 6) & (crashes_copy["Hour"] <= 9)])
        evening_rush = len(crashes_copy[(crashes_copy["Hour"] >= 16) & (crashes_copy["Hour"] <= 19)])
        st.caption(f"Morning Rush (6-9 AM): {morning_rush:,} crashes | Evening Rush (4-7 PM): {evening_rush:,} crashes")

    with col2:
        st.subheader("Crashes by Day of Week")

        day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        daily = crashes_copy.groupby("DayName").size().reindex(day_order).reset_index(name="Crashes")
        daily.columns = ["Day", "Crashes"]

        fig = px.bar(daily, x="Day", y="Crashes",
                     color="Crashes",
                     color_continuous_scale="Blues")
        fig.update_layout(margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig, width="stretch")

        weekend = len(crashes_copy[crashes_copy["DayOfWeek"] >= 5])
        weekday = len(crashes_copy[crashes_copy["DayOfWeek"] < 5])
        st.caption(f"Weekdays: {weekday:,} crashes | Weekends: {weekend:,} crashes")

    # Heat map
    st.subheader("Crash Heat Map (Hour x Day)")

    heatmap_data = crashes_copy.groupby(["DayOfWeek", "Hour"]).size().unstack(fill_value=0)
    heatmap_data.index = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    fig = px.imshow(
        heatmap_data,
        labels=dict(x="Hour of Day", y="Day of Week", color="Crashes"),
        color_continuous_scale="YlOrRd",
        aspect="auto"
    )
    fig.update_layout(margin=dict(t=20, b=20, l=20, r=20))
    st.plotly_chart(fig, width="stretch")

    # Monthly trend
    st.subheader("Monthly Trend")
    crashes_copy["YearMonth"] = crashes_copy["Start Time"].dt.to_period("M").astype(str)
    monthly = crashes_copy.groupby("YearMonth").size().reset_index(name="Crashes")

    fig = px.line(monthly, x="YearMonth", y="Crashes", markers=True)
    fig.update_layout(
        xaxis_title="Month",
        yaxis_title="Crashes",
        margin=dict(t=20, b=20, l=20, r=20)
    )
    st.plotly_chart(fig, width="stretch")


def display_crash_map(crashes: pd.DataFrame, roadwork: pd.DataFrame):
    """Display interactive crash map."""

    st.subheader("Crash Location Map")

    show_roadwork = st.checkbox("Show Active Roadwork Zones", value=True)

    county_geojson = load_geojson()

    if crashes.empty:
        mean_lat, mean_lon = 32.806671, -86.791130
    else:
        mean_lat = crashes["Start Latitude"].mean()
        mean_lon = crashes["Start Longitude"].mean()

    m = folium.Map(location=[mean_lat, mean_lon], zoom_start=7)

    # Add county boundaries
    folium.GeoJson(
        county_geojson,
        style_function=lambda x: {
            "fillColor": "transparent",
            "color": "gray",
            "weight": 1,
        },
    ).add_to(m)

    # Add roadwork zones if enabled
    if show_roadwork and not roadwork.empty:
        roadwork_group = folium.FeatureGroup(name="Roadwork Zones")
        for _, row in roadwork.head(100).iterrows():
            lat, lon = row.get("Start Latitude"), row.get("Start Longitude")
            if pd.notna(lat) and pd.notna(lon):
                folium.CircleMarker(
                    location=[lat, lon],
                    radius=15,
                    color="orange",
                    fill=True,
                    fillColor="orange",
                    fillOpacity=0.3,
                    popup=f"Roadwork: {row.get('Location', 'Unknown')}"
                ).add_to(roadwork_group)
        roadwork_group.add_to(m)

    # Add crash markers with clustering
    marker_cluster = plugins.MarkerCluster().add_to(m)

    # Extract columns for fast iteration
    lats = crashes["Start Latitude"].tolist()
    lons = crashes["Start Longitude"].tolist()
    locations = crashes["Location"].tolist()
    severities = crashes["Severity"].tolist()
    start_times = crashes["Start Time"].tolist()
    descriptions = crashes["Description"].tolist()

    for i in range(len(crashes)):
        lat, lon = lats[i], lons[i]
        if lat is None or lon is None or pd.isna(lat) or pd.isna(lon):
            continue

        severity = severities[i] or "Unknown"
        color = {"Major": "red", "Moderate": "orange", "Minor": "blue"}.get(severity, "gray")

        time_str = ""
        if pd.notna(start_times[i]):
            try:
                time_str = dt.strftime(start_times[i], "%m/%d %I:%M %p")
            except:
                time_str = str(start_times[i])[:16]

        popup_html = f"""
        <b>{severity} Crash</b><br>
        Location: {locations[i] or 'Unknown'}<br>
        Time: {time_str}<br>
        {(descriptions[i] or '')[:100]}
        """

        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_html, max_width=300),
            icon=folium.Icon(color=color, icon="car", prefix="fa"),
        ).add_to(marker_cluster)

    stf.folium_static(m, width=1200, height=600)

    # Legend
    st.caption("Red = Major | Orange = Moderate | Blue = Minor | Orange circles = Roadwork Zones")


def display_data_explorer(crashes: pd.DataFrame):
    """Display filterable data table."""

    st.subheader("Crash Data Explorer")

    # Column selection
    all_cols = crashes.columns.tolist()
    default_cols = ["Start Time", "Severity", "Location", "County", "Road", "Cross Street", "Description"]
    available_defaults = [c for c in default_cols if c in all_cols]

    selected_cols = st.multiselect(
        "Select columns to display",
        all_cols,
        default=available_defaults
    )

    if not selected_cols:
        selected_cols = available_defaults

    # Search filter
    search = st.text_input("Search (filters all columns)")

    display_df = crashes[selected_cols].copy()

    if search:
        mask = display_df.astype(str).apply(lambda x: x.str.contains(search, case=False, na=False)).any(axis=1)
        display_df = display_df[mask]

    # Format datetime columns
    for col in display_df.columns:
        if "Time" in col or "Updated" in col:
            display_df[col] = pd.to_datetime(display_df[col]).dt.strftime("%Y-%m-%d %H:%M")

    st.dataframe(display_df, width="stretch", height=500)

    # Download button
    csv = crashes.to_csv(index=False)
    st.download_button(
        "Download Full Dataset (CSV)",
        csv,
        file_name=f"alabama_crashes_{datetime.date.today()}.csv",
        mime="text/csv"
    )


if __name__ == "__main__":
    main()
