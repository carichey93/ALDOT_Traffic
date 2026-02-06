"""
About tab: methodology and site information.
"""

import streamlit as st


def display_about():
    """Display methodology and site information."""
    st.subheader("About This Dashboard")

    st.markdown("""
    This dashboard provides analytics on traffic crashes across Alabama using data from the
    Alabama Department of Transportation (ALDOT) AlgoTraffic API.
    """)

    st.divider()

    st.subheader("Data Source")
    st.markdown("""
    Data is pulled from the [ALDOT AlgoTraffic website](https://algotraffic.com/map).
    """)

    st.divider()

    st.subheader("Metrics & Calculations")

    st.markdown("#### Danger Score")
    st.markdown("""
    The danger score weights crashes by severity to identify the most hazardous locations:

    | Severity | Points |
    |----------|--------|
    | Major | 3 |
    | Moderate | 2 |
    | Minor | 1 |

    **Total Danger Score** = (Major crashes x 3) + (Moderate crashes x 2) + (Minor crashes x 1)

    This scoring system gives more weight to serious crashes when ranking roads and counties.
    """)

    st.markdown("#### Average Clearance Time")
    st.markdown("""
    Clearance time measures how long it takes to clear a crash from the roadway:

    - **Calculation:** End Time - Start Time (for each crash)
    - **Filters Applied:**
        - Only crashes with both start and end times recorded
        - Excludes durations under 1 minute (data errors)
        - Excludes durations over 24 hours (likely incomplete data)
    - **Result:** Average of all valid durations, displayed in minutes or hours
    """)

    st.markdown("#### Work Zone Crashes")
    st.markdown("""
    Estimates crashes occurring in or near active construction zones:

    - A crash is counted as "in/near work zone" if:
        1. It occurs on the same road AND county as active roadwork, AND
        2. If mile markers are available, the crash is within 2 miles of the roadwork location
    - This is an approximation since exact work zone boundaries aren't available
    """)

    st.markdown("#### Crash Hot Spots")
    st.markdown("""
    Identifies geographic clusters of crashes:

    - **Method:** Groups crashes within 0.5 miles of each other
    - **Minimum Cluster Size:** 3 crashes
    - **Distance Calculation:** Haversine formula (accounts for Earth's curvature)
    """)

    st.divider()

    st.subheader("Dashboard Tabs")

    st.markdown("""
    | Tab | Description |
    |-----|-------------|
    | **Overview** | Key metrics, severity breakdown, daily trends, and quick insights |
    | **Danger Rankings** | Most dangerous roads, counties, hot spots, and intersections |
    | **Time Analysis** | Hourly, daily, and monthly crash patterns with heat map |
    | **Crash Map** | Interactive map with crash locations and optional roadwork overlay |
    | **Data Explorer** | Searchable, filterable table with CSV export |
    """)

    st.divider()

    st.subheader("Filters")
    st.markdown("""
    Use the sidebar filters to customize your view:

    - **Time Period:** Today, Last 7 Days, Last 30 Days, This Year, or All Time
    - **County:** Filter to specific Alabama counties
    - **Severity:** Filter by crash severity (Major, Moderate, Minor)

    All metrics and visualizations update based on your filter selections.
    """)

    st.divider()

    st.subheader("Severity Levels")
    st.markdown("""
    ALDOT classifies crash severity based on impact to traffic:

    | Level | Description |
    |-------|-------------|
    | **Major** | Significant traffic impact, multiple lanes blocked, or extended duration |
    | **Moderate** | Notable traffic impact, partial lane blockage |
    | **Minor** | Minimal traffic impact, shoulder or single lane |
    """)

    st.divider()

    st.caption("Dashboard created with Streamlit, Plotly, and Folium")
