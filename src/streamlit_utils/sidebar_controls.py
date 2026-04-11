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
    """Render waveform controls and return the selected configuration.

    All widgets use stable ``key`` values so their state persists when
    the user navigates between Streamlit pages.
    """

    st.sidebar.header("Controles")
    window_start, window_end = st.sidebar.slider(
        "Ventana de tiempo (s)",
        min_value=0,
        max_value=3600,
        value=st.session_state.get("wf_time_window", (0, 300)),
        step=10,
        key="wf_time_window",
    )
    amplitude_scale = st.sidebar.selectbox(
        "Escala de amplitud",
        ["Auto", "Global", "Individual"],
        index=["Auto", "Global", "Individual"].index(
            st.session_state.get("wf_amplitude_scale", "Auto")
        ),
        key="wf_amplitude_scale",
    )
    unit = st.sidebar.selectbox(
        "Unidad",
        ["Raw", "m/s²", "g"],
        index=["Raw", "m/s²", "g"].index(
            st.session_state.get("wf_unit", "m/s²")
        ),
        key="wf_unit",
    )

    # Estaciones disponibles pueden cambiar al cargar un nuevo dataset.
    # Recuperar selección previa solo si sigue siendo válida.
    prev_selected = st.session_state.get("wf_selected_stations", [])
    valid_prev = [s for s in prev_selected if s in stations]
    default_selection = valid_prev if valid_prev else (stations[: min(len(stations), 3)] if stations else [])

    selected_stations = st.sidebar.multiselect(
        "Seleccionar estaciones",
        stations,
        default=default_selection,
        key="wf_selected_stations",
    )

    filter_type_opts = ["bandpass", "highpass", "lowpass", "none"]
    prev_filter = st.session_state.get("wf_filter_type", "bandpass")
    filter_idx = filter_type_opts.index(prev_filter) if prev_filter in filter_type_opts else 0

    filter_type = st.sidebar.selectbox(
        "Tipo de filtro",
        filter_type_opts,
        index=filter_idx,
        key="wf_filter_type",
    )
    freqmin = st.sidebar.number_input(
        "Frecuencia mínima (Hz)",
        min_value=0.1,
        max_value=50.0,
        value=float(st.session_state.get("wf_freqmin", 1.0)),
        step=0.1,
        key="wf_freqmin",
    )
    freqmax = st.sidebar.number_input(
        "Frecuencia máxima (Hz)",
        min_value=1.0,
        max_value=100.0,
        value=float(st.session_state.get("wf_freqmax", 10.0)),
        step=1.0,
        key="wf_freqmax",
    )

    return WaveformControls(
        time_window=(window_start, window_end),
        amplitude_scale=amplitude_scale,
        selected_stations=selected_stations,
        filter_type=filter_type,
        freqmin=freqmin,
        freqmax=freqmax,
        unit=unit,
    )
