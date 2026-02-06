"""
Data Explorer tab: searchable, filterable data table with CSV export.
"""

import datetime

import pandas as pd
import streamlit as st


def display_data_explorer(crashes: pd.DataFrame):
    """Display filterable data table."""
    st.subheader("Crash Data Explorer")

    all_cols = crashes.columns.tolist()
    default_cols = [
        "Start Time", "Severity", "Location", "County",
        "Road", "Cross Street", "Description",
    ]
    available_defaults = [c for c in default_cols if c in all_cols]

    selected_cols = st.multiselect(
        "Select columns to display", all_cols, default=available_defaults
    )

    if not selected_cols:
        selected_cols = available_defaults

    search = st.text_input("Search (filters all columns)")

    display_df = crashes[selected_cols].copy()

    if search:
        mask = (
            display_df.astype(str)
            .apply(lambda x: x.str.contains(search, case=False, na=False))
            .any(axis=1)
        )
        display_df = display_df[mask]

    for col in display_df.columns:
        if "Time" in col or "Updated" in col:
            display_df[col] = pd.to_datetime(display_df[col]).dt.strftime(
                "%Y-%m-%d %H:%M"
            )

    st.dataframe(display_df, width="stretch", height=500)

    csv = crashes.to_csv(index=False)
    st.download_button(
        "Download Full Dataset (CSV)",
        csv,
        file_name=f"alabama_crashes_{datetime.date.today()}.csv",
        mime="text/csv",
    )
