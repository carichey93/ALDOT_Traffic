"""
Main application module: sidebar, filters, data loading, and tab routing.
"""

import datetime

import streamlit as st

from app.config import (
    APPLE_TOUCH_ICON_HTML,
    CUSTOM_CSS,
    DATA_REFRESH_INTERVAL,
    PAGE_ICON,
    PAGE_TITLE,
)
from app.tabs.about import display_about
from app.tabs.crash_map import display_crash_map
from app.tabs.danger_rankings import display_danger_rankings
from app.tabs.data_explorer import display_data_explorer
from app.tabs.overview import display_overview
from app.tabs.time_analysis import display_time_analysis
from data.api import update_events
from data.database import get_last_update_time, get_unique_values, init_db, query_events


def configure_page():
    """Set Streamlit page config and inject custom HTML/CSS."""
    st.set_page_config(
        page_title=PAGE_TITLE,
        page_icon=PAGE_ICON,
        layout="wide",
    )
    st.markdown(APPLE_TOUCH_ICON_HTML, unsafe_allow_html=True)
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def check_and_update_db():
    """Update database if data is stale (older than refresh interval)."""
    last_update = get_last_update_time()
    if (
        last_update is None
        or (datetime.datetime.utcnow() - last_update).total_seconds()
        > DATA_REFRESH_INTERVAL
    ):
        with st.spinner("Fetching latest data..."):
            update_events()
        st.cache_data.clear()


def get_date_range_from_selection(selection: str) -> tuple:
    """Convert selection to date range and period label."""
    today = datetime.date.today()

    ranges = {
        "Today": (today, today, "yesterday"),
        "Last 7 Days": (today - datetime.timedelta(days=7), today, "prior 7 days"),
        "Last 30 Days": (today - datetime.timedelta(days=30), today, "prior 30 days"),
        "This Year": (
            datetime.date(today.year, 1, 1),
            today,
            "same period last year",
        ),
        "All Time": (datetime.date(2019, 1, 1), today, None),
    }
    return ranges.get(selection, (today, today, None))


def get_previous_period(start_date, end_date, selection: str) -> tuple:
    """Get the previous period for comparison."""
    if selection == "All Time":
        return None, None

    days_in_period = (end_date - start_date).days + 1

    if selection == "This Year":
        prev_end = end_date.replace(year=end_date.year - 1)
        prev_start = start_date.replace(year=start_date.year - 1)
    else:
        prev_end = start_date - datetime.timedelta(days=1)
        prev_start = prev_end - datetime.timedelta(days=days_in_period - 1)

    return prev_start, prev_end


def run():
    """Main application entry point."""
    configure_page()
    init_db()

    # Header
    col_logo, col_title = st.columns([1, 4])
    with col_logo:
        st.image("website_logo.png", width=100)
    with col_title:
        st.title(PAGE_TITLE)

    # Sidebar
    with st.sidebar:
        st.header("Dashboard Controls")
        check_and_update_db()

        date_range = st.selectbox(
            "Time Period",
            ["Today", "Last 7 Days", "Last 30 Days", "This Year", "All Time"],
            index=2,
        )

        start_date, end_date, period_label = get_date_range_from_selection(date_range)
        prev_start, prev_end = get_previous_period(start_date, end_date, date_range)

        counties = get_unique_values("County")
        selected_counties = st.multiselect(
            "Filter by County", ["All"] + sorted(counties), default=["All"]
        )

        selected_severities = st.multiselect(
            "Severity",
            ["All", "Major", "Moderate", "Minor"],
            default=["All"],
        )

        st.divider()
        last_update = get_last_update_time()
        if last_update:
            local_time = last_update.replace(
                tzinfo=datetime.timezone.utc
            ).astimezone()
            st.caption(f"Last updated: {local_time.strftime('%Y-%m-%d %H:%M')}")
        else:
            st.caption("Last updated: Never")

        st.divider()
        st.markdown(
            """
            <a href="https://www.buymeacoffee.com/mzyejstdb" target="_blank">
                <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png"
                     alt="Buy Me A Coffee"
                     style="height: 40px; width: 145px;">
            </a>
            """,
            unsafe_allow_html=True,
        )

    # Load data
    county_filter = (
        selected_counties if "All" not in selected_counties else None
    )
    severity_filter = (
        selected_severities if "All" not in selected_severities else None
    )

    crashes = query_events(
        start_date=start_date,
        end_date=end_date,
        counties=county_filter,
        categories=["Crash"],
        severities=severity_filter,
    )

    prev_crashes = query_events(
        start_date=prev_start,
        end_date=prev_end,
        counties=county_filter,
        categories=["Crash"],
        severities=severity_filter,
    )

    roadwork = query_events(
        start_date=start_date,
        end_date=end_date,
        categories=["Roadwork"],
    )

    if crashes.empty:
        st.warning("No crash data found for the selected filters.")
        return

    # Tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        ["Overview", "Danger Rankings", "Time Analysis", "Crash Map", "Data Explorer", "About"]
    )

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

    with tab6:
        display_about()
