"""Map helpers: click-to-pin on the report form, browse-only map of saved reports."""

from uuid import uuid4

import folium
import streamlit as st
from streamlit_folium import st_folium

from models.schemas import Report, ReportType
from utils.locations import report_points

PINS_KEY = "location_pins"
DEFAULT_CENTER = (50.8514, 5.6900)
DEFAULT_RADIUS = 200.0
LOST_COLOR = "#3b82f6"
FOUND_COLOR = "#22c55e"


def pins(session_key: str = PINS_KEY) -> list[dict]:
    return list(st.session_state.get(session_key, []))


def _ensure_pins(session_key: str = PINS_KEY) -> list[dict]:
    if session_key not in st.session_state:
        st.session_state[session_key] = []
    return st.session_state[session_key]


def replace_pins(new_pins: list[dict], session_key: str = PINS_KEY) -> None:
    st.session_state[session_key] = new_pins


def add_pin(
    lat: float,
    lon: float,
    radius_meters: float = DEFAULT_RADIUS,
    session_key: str = PINS_KEY,
) -> None:
    current = _ensure_pins(session_key)
    current.append(
        {
            "id": str(uuid4()),
            "lat": float(lat),
            "lon": float(lon),
            "radius_meters": float(radius_meters),
            "label": f"Pin {len(current) + 1}",
        }
    )


def render_location_map(
    *,
    map_key: str,
    height: int = 420,
    extra_layers: list | None = None,
    session_key: str = PINS_KEY,
    interactive: bool = True,
) -> None:
    current = _ensure_pins(session_key)
    if current:
        latitude = current[-1]["lat"]
        longitude = current[-1]["lon"]
        zoom = 14
    else:
        latitude, longitude = DEFAULT_CENTER
        zoom = 13

    fmap = folium.Map(location=[latitude, longitude], zoom_start=zoom)
    for layer in extra_layers or []:
        layer.add_to(fmap)
    for pin in current:
        folium.Circle(
            location=[pin["lat"], pin["lon"]],
            radius=pin["radius_meters"],
            color=LOST_COLOR,
            weight=1,
            fill=True,
            fill_opacity=0.12,
        ).add_to(fmap)
        folium.Marker(
            location=[pin["lat"], pin["lon"]],
            tooltip=pin.get("label", "Pin"),
        ).add_to(fmap)

    result = st_folium(
        fmap,
        height=height,
        use_container_width=True,
        key=map_key,
        returned_objects=["last_clicked"] if interactive else [],
    )
    if not interactive:
        return
    last = (result or {}).get("last_clicked")
    click_key = f"{map_key}_last_click"
    if last and "lat" in last and "lng" in last:
        signature = (round(last["lat"], 6), round(last["lng"], 6))
        if st.session_state.get(click_key) != signature:
            st.session_state[click_key] = signature
            add_pin(last["lat"], last["lng"], session_key=session_key)
            st.rerun()


def render_pin_details(session_key: str = PINS_KEY) -> None:
    current = _ensure_pins(session_key)
    if not current:
        st.caption("No pins yet. Click the map to add a possible location.")
        return

    for index, pin in enumerate(list(current)):
        with st.container(border=True):
            st.write(f"**{pin.get('label', f'Pin {index + 1}')}**")
            st.caption(f"{pin['lat']:.5f}, {pin['lon']:.5f}")
            pin["radius_meters"] = float(
                st.slider(
                    "Range (m)",
                    min_value=10,
                    max_value=5000,
                    value=int(pin["radius_meters"]),
                    step=10,
                    key=f"pin-radius-{pin['id']}",
                )
            )
            if st.button("Remove", key=f"pin-remove-{pin['id']}"):
                current.pop(index)
                st.rerun()
    if st.button("Clear all pins"):
        st.session_state[session_key] = []
        st.rerun()


def render_reports_map(reports: list[Report], *, height: int = 560) -> None:
    """Browse saved reports. Clicks do not create new pins."""
    fmap = folium.Map(location=list(DEFAULT_CENTER), zoom_start=13)
    points: list[tuple[float, float]] = []
    for report in reports:
        color = LOST_COLOR if report.report_type == ReportType.LOST else FOUND_COLOR
        kind = report.report_type.value
        for latitude, longitude, radius in report_points(report):
            points.append((latitude, longitude))
            if radius:
                folium.Circle(
                    location=[latitude, longitude],
                    radius=radius,
                    color=color,
                    weight=1,
                    fill=True,
                    fill_opacity=0.08,
                ).add_to(fmap)
            folium.CircleMarker(
                location=[latitude, longitude],
                radius=7,
                color=color,
                fill=True,
                fill_opacity=0.85,
                tooltip=f"{kind}: {report.description[:80]}",
            ).add_to(fmap)
    if len(points) >= 2:
        fmap.fit_bounds([[lat, lon] for lat, lon in points], padding=(30, 30))
    elif points:
        fmap.location = list(points[0])
    st_folium(
        fmap,
        height=height,
        use_container_width=True,
        key="browse-reports-map",
        returned_objects=[],
    )
