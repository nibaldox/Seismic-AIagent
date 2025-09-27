"""Helpers for handling Plotly interactions inside Streamlit."""

from __future__ import annotations

import importlib
from typing import Any, Dict, List


def capture_click_events(
    fig,
    *,
    key: str = "plotly_events",
    override_height: int | None = None,
    override_width: int | None = None,
    use_container_width: bool = True,
) -> List[Dict[str, Any]]:
    """Return Plotly click events in a minimal, type-safe structure."""

    try:
        module = importlib.import_module("streamlit_plotly_events")
    except ModuleNotFoundError:  # pragma: no cover - defensive fallback
        import streamlit as st

        st.plotly_chart(fig, use_container_width=use_container_width)
        return []

    plotly_events = getattr(module, "plotly_events")

    events = plotly_events(
        fig,
        click_event=True,
        select_event=False,
        hover_event=False,
        override_height=override_height,
        override_width=override_width,
        key=key,
    )
    return events or []
