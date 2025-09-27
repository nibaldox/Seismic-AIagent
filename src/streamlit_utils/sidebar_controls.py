"""Common sidebar controls for waveform exploration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import streamlit as st


@dataclass
class WaveformControls:
    """Container for user-selected waveform parameters."""

    time_window: Tuple[int, int]
    amplitude_scale: str
    selected_stations: List[str]
    filter_type: str
    freqmin: float
    freqmax: float
    unit: str


def render_waveform_sidebar(stations: List[str]) -> WaveformControls:
    """Render waveform controls and return the selected configuration."""

    st.sidebar.header("Controls")
    window_start, window_end = st.sidebar.slider(
        "Time Window (s)",
        min_value=0,
        max_value=3600,
        value=(0, 300),
        step=10,
    )
    amplitude_scale = st.sidebar.selectbox(
        "Amplitude Scale",
        ["Auto", "Global", "Individual"],
        index=0,
    )
    unit = st.sidebar.selectbox(
        "Unit",
        ["Raw", "m/s²", "g"],
        index=1,  # Default to m/s²
    )
    default_selection = stations[: min(len(stations), 3)] if stations else []
    selected_stations = st.sidebar.multiselect(
        "Select Stations",
        stations,
        default=default_selection,
    )
    filter_type = st.sidebar.selectbox(
        "Filter Type",
        ["bandpass", "highpass", "lowpass", "none"],
        index=0,
    )
    freqmin = st.sidebar.number_input("Min Frequency (Hz)", min_value=0.1, max_value=50.0, value=1.0)
    freqmax = st.sidebar.number_input("Max Frequency (Hz)", min_value=1.0, max_value=100.0, value=10.0)

    return WaveformControls(
        time_window=(window_start, window_end),
        amplitude_scale=amplitude_scale,
        selected_stations=selected_stations,
        filter_type=filter_type,
        freqmin=freqmin,
        freqmax=freqmax,
        unit=unit,
    )
