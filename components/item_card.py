"""Report summary component."""

from pathlib import Path

import streamlit as st

from models.schemas import Report
from utils.locations import report_points


def _preview(text: str, limit: int = 90) -> str:
    cleaned = text.strip().replace("\n", " ")
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1] + "…"


def _first_image(report: Report) -> str | None:
    for path in report.image_paths:
        if Path(path).is_file():
            return path
    return None


def render_item_card(report: Report) -> None:
    """Render a compact report summary from the shared contract."""
    heading = report.category or report.report_type.value.title()
    points = report_points(report)
    with st.container(border=True):
        image = _first_image(report)
        if image:
            st.image(image, width="stretch")
        st.subheader(heading)
        st.write(report.description)
        if report.holding_note:
            st.caption(f"Where it is now: {report.holding_note}")
        details = [
            report.report_type.value.title(),
            report.status.value,
        ]
        if points:
            details.append(f"{len(points)} location pin(s)")
        st.caption(" · ".join(details))


def render_item_tile(report: Report, *, selected: bool, button_key: str) -> bool:
    """Compact grid tile. Returns True when the user chooses this item."""
    heading = report.category or report.report_type.value.title()
    with st.container(border=True):
        if selected:
            st.caption("Selected")
        image = _first_image(report)
        if image:
            st.image(image, width="stretch")
        else:
            st.caption("No photo")
        st.markdown(f"**{heading}**")
        st.write(_preview(report.description))
        if report.holding_note:
            st.caption(_preview(report.holding_note, 60))
        return st.button(
            "Matching this" if selected else "Match this",
            type="primary" if selected else "secondary",
            width="stretch",
            key=button_key,
        )
