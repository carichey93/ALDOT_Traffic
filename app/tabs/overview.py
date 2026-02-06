"""
Overview tab: key metrics, severity breakdown, daily trends, and quick insights.
"""

import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from app.calculations import (
    calculate_avg_clearance_minutes,
    calculate_avg_clearance_time,
    calculate_construction_zone_crashes,
)
from app.config import SEVERITY_COLORS


def display_overview(
    crashes: pd.DataFrame,
    prev_crashes: pd.DataFrame,
    roadwork: pd.DataFrame,
    start_date,
    end_date,
    period_label: str,
):
    """Display overview metrics and insights."""
    total_crashes = len(crashes)
    prev_total = (
        len(prev_crashes)
        if prev_crashes is not None and not prev_crashes.empty
        else 0
    )
    major_crashes = len(crashes[crashes["Severity"] == "Major"])
    prev_major = (
        len(prev_crashes[prev_crashes["Severity"] == "Major"])
        if prev_crashes is not None and not prev_crashes.empty
        else 0
    )
    moderate_crashes = len(crashes[crashes["Severity"] == "Moderate"])
    prev_moderate = (
        len(prev_crashes[prev_crashes["Severity"] == "Moderate"])
        if prev_crashes is not None and not prev_crashes.empty
        else 0
    )

    construction_crashes = calculate_construction_zone_crashes(crashes, roadwork)
    avg_clearance = calculate_avg_clearance_time(crashes)
    avg_clearance_mins = calculate_avg_clearance_minutes(crashes)
    prev_clearance_mins = calculate_avg_clearance_minutes(prev_crashes)

    def pct_change(current, previous, label):
        if previous == 0 or label is None:
            return None, None
        pct = ((current - previous) / previous) * 100
        if pct > 0:
            return f"+{pct:.1f}% from {label}", pct
        return f"{pct:.1f}% from {label}", pct

    # Top metrics row
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        delta, _ = pct_change(total_crashes, prev_total, period_label)
        st.metric(
            "Total Crashes", f"{total_crashes:,}", delta=delta, delta_color="inverse"
        )
    with col2:
        delta, _ = pct_change(major_crashes, prev_major, period_label)
        st.metric("Major", f"{major_crashes:,}", delta=delta, delta_color="inverse")
    with col3:
        delta, _ = pct_change(moderate_crashes, prev_moderate, period_label)
        st.metric(
            "Moderate", f"{moderate_crashes:,}", delta=delta, delta_color="inverse"
        )
    with col4:
        pct_in_workzone = (
            f"{100 * construction_crashes / total_crashes:.1f}% of total"
            if total_crashes
            else "0%"
        )
        st.metric(
            "In/Near Work Zones",
            f"{construction_crashes:,}",
            delta=pct_in_workzone,
            delta_color="off",
        )
    with col5:
        clearance_delta = None
        if avg_clearance_mins and prev_clearance_mins and period_label:
            diff = avg_clearance_mins - prev_clearance_mins
            if abs(diff) >= 1:
                clearance_delta = f"{diff:+.0f} min from {period_label}"
        st.metric(
            "Avg Clearance",
            avg_clearance,
            delta=clearance_delta,
            delta_color="inverse",
        )

    st.divider()

    # Charts
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Crashes by Severity")
        severity_counts = crashes["Severity"].value_counts()
        fig = px.pie(
            values=severity_counts.values,
            names=severity_counts.index,
            color=severity_counts.index,
            color_discrete_map=SEVERITY_COLORS,
            hole=0.4,
        )
        fig.update_layout(margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig, width="stretch")

    with col2:
        st.subheader("Daily Crash Trend")
        crashes_copy = crashes.copy()
        crashes_copy["Date"] = pd.to_datetime(crashes_copy["Start Time"]).dt.date
        daily_counts = crashes_copy.groupby("Date").size().reset_index(name="Crashes")
        fig = px.area(
            daily_counts, x="Date", y="Crashes", color_discrete_sequence=["#667eea"]
        )
        fig.update_layout(margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig, width="stretch")

    # Quick insights
    st.subheader("Quick Insights")
    col1, col2, col3, col4 = st.columns(4)

    crashes_copy["Start Time"] = pd.to_datetime(crashes_copy["Start Time"])
    crashes_copy["DayOfWeek"] = crashes_copy["Start Time"].dt.day_name()
    crashes_copy["Hour"] = crashes_copy["Start Time"].dt.hour

    with col1:
        worst_date = crashes_copy["Date"].value_counts().idxmax()
        worst_date_count = crashes_copy["Date"].value_counts().max()
        worst_date_str = (
            worst_date.strftime("%b %d, %Y")
            if hasattr(worst_date, "strftime")
            else str(worst_date)
        )
        st.info(f"**Worst Date:** {worst_date_str} ({worst_date_count:,} crashes)")

    with col2:
        worst_day = crashes_copy["DayOfWeek"].value_counts().idxmax()
        worst_day_count = crashes_copy["DayOfWeek"].value_counts().max()
        st.info(f"**Worst Day of Week:** {worst_day} ({worst_day_count:,} crashes)")

    with col3:
        worst_hour = int(crashes_copy["Hour"].value_counts().idxmax())
        worst_hour_count = crashes_copy["Hour"].value_counts().max()
        hour_ampm = (
            datetime.datetime.strptime(f"{worst_hour}:00", "%H:%M")
            .strftime("%I:%M %p")
            .lstrip("0")
        )
        st.info(f"**Worst Hour:** {hour_ampm} ({worst_hour_count:,} crashes)")

    with col4:
        worst_county = crashes["County"].value_counts().idxmax()
        worst_county_count = crashes["County"].value_counts().max()
        st.info(f"**Worst County:** {worst_county} ({worst_county_count:,} crashes)")
