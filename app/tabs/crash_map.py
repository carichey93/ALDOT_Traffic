"""
Crash Map tab: interactive Folium map with crash markers and roadwork overlay.
"""

from datetime import datetime as dt

import folium
import folium.plugins as plugins
import geopandas as gpd
import pandas as pd
import streamlit as st
import streamlit_folium as stf

from app.config import GEOJSON_FILE, SEVERITY_MAP_COLORS


@st.cache_data(ttl=300)
def _load_geojson():
    """Load and cache the GeoJSON file."""
    return gpd.read_file(GEOJSON_FILE)


def display_crash_map(crashes: pd.DataFrame, roadwork: pd.DataFrame):
    """Display interactive crash map."""
    st.subheader("Crash Location Map")

    show_roadwork = st.checkbox("Show Active Roadwork Zones", value=True)

    county_geojson = _load_geojson()

    if crashes.empty:
        mean_lat, mean_lon = 32.806671, -86.791130
    else:
        mean_lat = crashes["Start Latitude"].mean()
        mean_lon = crashes["Start Longitude"].mean()

    m = folium.Map(location=[mean_lat, mean_lon], zoom_start=7)

    # County boundaries
    folium.GeoJson(
        county_geojson,
        style_function=lambda x: {
            "fillColor": "transparent",
            "color": "gray",
            "weight": 1,
        },
    ).add_to(m)

    # Roadwork zones
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
                    popup=f"Roadwork: {row.get('Location', 'Unknown')}",
                ).add_to(roadwork_group)
        roadwork_group.add_to(m)

    # Crash markers with clustering
    marker_cluster = plugins.MarkerCluster().add_to(m)

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
        color = SEVERITY_MAP_COLORS.get(severity, "gray")

        time_str = ""
        if pd.notna(start_times[i]):
            try:
                time_str = dt.strftime(start_times[i], "%m/%d %I:%M %p")
            except Exception:
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

    st.caption(
        "Red = Major | Orange = Moderate | Blue = Minor | "
        "Orange circles = Roadwork Zones"
    )
