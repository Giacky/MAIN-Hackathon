"""Geographic search and location picker."""

import folium
import streamlit as st

from database.repository import SQLiteRepository
from models.schemas import ReportType
from utils.map_pin import render_location_map, render_pin_details


@st.cache_resource
def _repository() -> SQLiteRepository:
    return SQLiteRepository()


def _report_points(report) -> list[tuple[float, float, float]]:
    if report.locations:
        return [
            (item.latitude, item.longitude, item.radius_meters)
            for item in report.locations
        ]
    if report.latitude is None or report.longitude is None:
        return []
    return [(report.latitude, report.longitude, report.radius_meters or 0)]


def _report_markers() -> folium.FeatureGroup:
    layer = folium.FeatureGroup(name="Saved reports")
    for report in _repository().list_reports():
        color = "#3b82f6" if report.report_type == ReportType.LOST else "#22c55e"
        for latitude, longitude, radius in _report_points(report):
            if radius:
                folium.Circle(
                    location=[latitude, longitude],
                    radius=radius,
                    color=color,
                    weight=1,
                    fill=True,
                    fill_opacity=0.08,
                ).add_to(layer)
            folium.CircleMarker(
                location=[latitude, longitude],
                radius=7,
                color=color,
                fill=True,
                fill_opacity=0.85,
                tooltip=f"{report.report_type.value}: {report.description[:80]}",
            ).add_to(layer)
    return layer


def render() -> None:
    st.title("Map")
    st.caption(
        "Add as many guesses as you like, or none. Saved reports are blue (lost) and green (found)."
    )

    map_col, detail_col = st.columns([1.7, 1], gap="large")
    with map_col:
        with st.container(border=True):
            st.subheader("Choose locations", icon=":material/map:")
            render_location_map(
                map_key="map_page",
                height=560,
                extra_layers=[_report_markers()],
            )
    with detail_col:
        with st.container(border=True):
            st.subheader("Pin details", icon=":material/place:")
            render_pin_details()
