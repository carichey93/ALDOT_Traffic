"""
Time Analysis tab: hourly, daily, and monthly crash patterns with heat map.
"""

import datetime

import pandas as pd
import plotly.express as px
import streamlit as st


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
        _display_hourly_chart(crashes_copy)

    with col2:
        st.subheader("Crashes by Day of Week")
        _display_daily_chart(crashes_copy)

    # Heat map
    st.subheader("Crash Heat Map (Hour x Day)")
    _display_heatmap(crashes_copy)

    # Monthly trend
    st.subheader("Monthly Trend")
    _display_monthly_trend(crashes_copy)


def _display_hourly_chart(crashes: pd.DataFrame):
    """Render hourly crash bar chart with rush hour stats."""
    hourly = crashes.groupby("Hour").size().reset_index(name="Crashes")
    hourly["Hour Label"] = hourly["Hour"].apply(
        lambda h: datetime.datetime.strptime(f"{int(h)}:00", "%H:%M")
        .strftime("%I %p")
        .lstrip("0")
    )
    fig = px.bar(
        hourly,
        x="Hour Label",
        y="Crashes",
        color="Crashes",
        color_continuous_scale="Reds",
    )
    fig.update_layout(xaxis_title="Hour", margin=dict(t=20, b=20, l=20, r=20))
    st.plotly_chart(fig, width="stretch")

    morning_rush = len(crashes[(crashes["Hour"] >= 6) & (crashes["Hour"] <= 9)])
    evening_rush = len(crashes[(crashes["Hour"] >= 16) & (crashes["Hour"] <= 19)])
    st.caption(
        f"Morning Rush (6-9 AM): {morning_rush:,} crashes | "
        f"Evening Rush (4-7 PM): {evening_rush:,} crashes"
    )


def _display_daily_chart(crashes: pd.DataFrame):
    """Render daily crash bar chart with weekday/weekend stats."""
    day_order = [
        "Monday", "Tuesday", "Wednesday", "Thursday",
        "Friday", "Saturday", "Sunday",
    ]
    daily = (
        crashes.groupby("DayName")
        .size()
        .reindex(day_order)
        .reset_index(name="Crashes")
    )
    daily = daily.rename(columns={"DayName": "Day"})

    fig = px.bar(
        daily,
        x="Day",
        y="Crashes",
        color="Crashes",
        color_continuous_scale="Blues",
    )
    fig.update_layout(margin=dict(t=20, b=20, l=20, r=20))
    st.plotly_chart(fig, width="stretch")

    weekend = len(crashes[crashes["DayOfWeek"] >= 5])
    weekday = len(crashes[crashes["DayOfWeek"] < 5])
    st.caption(f"Weekdays: {weekday:,} crashes | Weekends: {weekend:,} crashes")


def _display_heatmap(crashes: pd.DataFrame):
    """Render hour-by-day crash heatmap."""
    heatmap_data = (
        crashes.groupby(["DayOfWeek", "Hour"]).size().unstack(fill_value=0)
    )
    day_labels = {
        0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu",
        4: "Fri", 5: "Sat", 6: "Sun",
    }
    heatmap_data.index = heatmap_data.index.map(day_labels)

    fig = px.imshow(
        heatmap_data,
        labels=dict(x="Hour of Day", y="Day of Week", color="Crashes"),
        color_continuous_scale="YlOrRd",
        aspect="auto",
    )
    fig.update_layout(margin=dict(t=20, b=20, l=20, r=20))
    st.plotly_chart(fig, width="stretch")


def _display_monthly_trend(crashes: pd.DataFrame):
    """Render monthly crash trend line chart."""
    crashes["YearMonth"] = crashes["Start Time"].dt.to_period("M").astype(str)
    monthly = crashes.groupby("YearMonth").size().reset_index(name="Crashes")

    fig = px.line(monthly, x="YearMonth", y="Crashes", markers=True)
    fig.update_layout(
        xaxis_title="Month",
        yaxis_title="Crashes",
        margin=dict(t=20, b=20, l=20, r=20),
    )
    st.plotly_chart(fig, width="stretch")
