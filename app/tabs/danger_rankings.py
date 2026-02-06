"""
Danger Rankings tab: most dangerous roads, counties, hot spots, and intersections.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.calculations import find_crash_clusters


def display_danger_rankings(crashes: pd.DataFrame):
    """Display danger rankings and leaderboards."""
    st.caption(
        "**Danger Score Calculation:** Major crashes = 3 points, "
        "Moderate = 2 points, Minor = 1 point"
    )

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Most Dangerous Roads")
        _display_danger_table(
            crashes, group_col="Road", header_color="#667eea", label="Road"
        )

    with col2:
        st.subheader("Most Dangerous Counties")
        _display_danger_table(
            crashes, group_col="County", header_color="#764ba2", label="County"
        )

    st.divider()

    # Hot spots
    st.subheader("Crash Hot Spots")
    st.caption("Locations with 3+ crashes within 0.5 miles of each other")

    cluster_stats = find_crash_clusters(crashes, radius_miles=0.5)

    if not cluster_stats.empty:
        display_clusters = cluster_stats.reset_index(drop=True)[
            ["Location", "Road", "County", "Crashes"]
        ].head(20)
        st.dataframe(display_clusters, width="stretch", hide_index=True)
    else:
        st.info(
            "No crash clusters found in this time period "
            "(requires 3+ crashes within 0.5 miles)."
        )

    # Dangerous intersections
    st.subheader("Dangerous Intersections")
    cross_street_crashes = crashes[
        crashes["Cross Street"].notna() & (crashes["Cross Street"] != "")
    ]

    if not cross_street_crashes.empty:
        intersection_stats = (
            cross_street_crashes.groupby(["Road", "Cross Street", "County"])
            .size()
            .reset_index(name="Crashes")
        )
        intersection_stats = intersection_stats.sort_values(
            "Crashes", ascending=False
        ).head(15)
        st.dataframe(intersection_stats, width="stretch", hide_index=True)
    else:
        st.info("No intersection data available.")


def _display_danger_table(
    crashes: pd.DataFrame, group_col: str, header_color: str, label: str
):
    """Render a danger score table for a given grouping column."""
    stats = crashes.groupby(group_col).agg(
        Total=("Event ID", "count"),
        Major=("Severity", lambda x: (x == "Major").sum()),
        Moderate=("Severity", lambda x: (x == "Moderate").sum()),
        Minor=("Severity", lambda x: (x == "Minor").sum()),
    )
    stats["Score"] = (
        stats["Major"] * 3 + stats["Moderate"] * 2 + stats["Minor"] * 1
    )
    stats = stats.sort_values("Score", ascending=False).head(15)

    fig = go.Figure(
        data=[
            go.Table(
                header=dict(
                    values=[
                        f"<b>{label}</b>",
                        "<b>Total</b>",
                        "<b>Major</b>",
                        "<b>Moderate</b>",
                        "<b>Minor</b>",
                        "<b>Score</b>",
                    ],
                    fill_color=header_color,
                    font=dict(color="white", size=12),
                    align="left",
                ),
                cells=dict(
                    values=[
                        stats.index,
                        stats["Total"],
                        stats["Major"],
                        stats["Moderate"],
                        stats["Minor"],
                        stats["Score"],
                    ],
                    fill_color=[
                        ["#f0f2f6", "#ffffff"] * (len(stats) // 2 + 1)
                    ],
                    align="left",
                ),
            )
        ]
    )
    fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=400)
    st.plotly_chart(fig, width="stretch")
