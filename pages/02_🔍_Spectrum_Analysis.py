"""Spectral analysis page."""

from __future__ import annotations

import streamlit as st

from src.streamlit_utils.session_state import (
    get_current_stream_name,
    get_selected_trace,
    get_selected_trace_label,
    get_session,
    list_dataset_names,
    set_current_stream,
)
from src.visualization.spectrum_plots import create_spectrogram


def main() -> None:
    st.header("🔍 Spectrum Analysis")
    session = get_session()

    dataset_names = list_dataset_names(session=session)
    current_dataset = get_current_stream_name(session=session)
    if dataset_names:
        selected_dataset = st.selectbox(
            "Active dataset",
            options=dataset_names,
            index=dataset_names.index(current_dataset) if current_dataset in dataset_names else 0,
            key="spectrum_active_dataset",
        )
        if selected_dataset and selected_dataset != current_dataset:
            set_current_stream(selected_dataset, session=session)
            current_dataset = selected_dataset

    trace = get_selected_trace(session)
    if trace is None:
        st.info("Select a trace from the waveform viewer to analyze its spectrum.")
        return

    fig = create_spectrogram(trace)
    st.plotly_chart(fig, use_container_width=True)
    label = get_selected_trace_label(session)
    if label:
        st.caption(f"Trace analizada: {label}")


if __name__ == "__main__":  # pragma: no cover
    main()
