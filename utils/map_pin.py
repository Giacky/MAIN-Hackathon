"""Click-to-pin map helpers shared by report and map pages."""

from uuid import uuid4

import folium
import streamlit as st
from streamlit_folium import st_folium

PINS_KEY = "location_pins"
DEFAULT_CENTER = (50.8514, 5.6900)
DEFAULT_RADIUS = 200.0


def pins() -> list[dict]:
    return list(st.session_state.get(PINS_KEY, []))


def _ensure_pins() -> list[dict]:
    if PINS_KEY not in st.session_state:
        st.session_state[PINS_KEY] = []
    return st.session_state[PINS_KEY]


def replace_pins(new_pins: list[dict]) -> None:
    st.session_state[PINS_KEY] = new_pins


def add_pin(lat: float, lon: float, radius_meters: float = DEFAULT_RADIUS) -> None:
    current = _ensure_pins()
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
) -> None:
    current = _ensure_pins()
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
            color="#2563eb",
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
        key=map_key,
        returned_objects=["last_clicked"],
        width="stretch",
    )
    last = (result or {}).get("last_clicked")
    click_key = f"{map_key}_last_click"
    if last and "lat" in last and "lng" in last:
        signature = (round(last["lat"], 6), round(last["lng"], 6))
        if st.session_state.get(click_key) != signature:
            st.session_state[click_key] = signature
            add_pin(last["lat"], last["lng"])
            st.rerun()


def render_pin_details() -> None:
    current = _ensure_pins()
    if not current:
        st.caption("No pins yet. Click the map to add a guess.")
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
        st.session_state[PINS_KEY] = []
        st.rerun()
