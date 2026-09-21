"""Report summary component."""

from pathlib import Path

import streamlit as st

from models.schemas import Report
from utils.locations import report_points


def render_item_card(report: Report) -> None:
    """Render a compact report summary from the shared contract."""
    heading = report.category or report.report_type.value.title()
    points = report_points(report)
    with st.container(border=True):
        text_column, photo_column = st.columns([3, 1])
        with text_column:
            st.subheader(heading)
            st.write(report.description)
            details = [
                report.report_type.value.title(),
                report.status.value,
            ]
            if points:
                details.append(f"{len(points)} location pin(s)")
            st.caption(" · ".join(details))
        with photo_column:
            shown = False
            for path in report.image_paths:
                if Path(path).is_file():
                    st.image(path, width="stretch")
                    shown = True
                    break
            if not shown:
                st.caption("No photo")
