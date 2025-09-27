"""Waveform viewer page."""

from __future__ import annotations

from typing import Any, Iterable

import streamlit as st

from src.core.data_reader import DataReader
from src.streamlit_utils.file_uploader import seismic_file_uploader
from src.streamlit_utils.plot_interactions import capture_click_events
from src.streamlit_utils.session_state import (
    get_current_stream,
    get_current_stream_name,
    get_selected_trace_label,
    get_session,
    get_traces_by_labels,
    list_dataset_names,
    list_trace_labels,
    register_stream,
    set_current_stream,
    set_selected_trace,
)
from src.streamlit_utils.sidebar_controls import render_waveform_sidebar
from src.visualization.waveform_plots import create_waveform_plot
from src.core.picking import suggest_picks_sta_lta, Pick, PickManager
from src.streamlit_utils.session_state import add_pick, list_picks, clear_picks
from src.core.magnitude import (
    estimate_local_magnitude,  # placeholder (mantener compatibilidad)
    estimate_local_magnitude_wa,
)


def _extract_traces(stream_container: Any) -> Iterable[Any]:
    if stream_container is None:
        return []
    if hasattr(stream_container, "traces"):
        return list(stream_container.traces)
    if hasattr(stream_container, "__iter__") and not isinstance(stream_container, (str, bytes)):
        return list(stream_container)
    if isinstance(stream_container, Iterable):
        return stream_container
    return []


def main() -> None:
    st.header("📊 Waveform Viewer")
    session = get_session()
    reader = DataReader()

    dataset_names = list_dataset_names(session=session)
    current_dataset = get_current_stream_name(session=session)
    if dataset_names:
        selected_dataset = st.selectbox(
            "Active dataset",
            options=dataset_names,
            index=dataset_names.index(current_dataset) if current_dataset in dataset_names else 0,
            key="waveform_active_dataset",
        )
        if selected_dataset and selected_dataset != current_dataset:
            set_current_stream(selected_dataset, session=session)
            current_dataset = selected_dataset

    uploaded_files = seismic_file_uploader("Upload seismic files", accept_multiple=False)
    if uploaded_files:
        uploaded_file = uploaded_files[0]
        try:
            loaded = reader.load_bytes(buffer=uploaded_file, format_hint=None)
        except Exception as exc:  # pragma: no cover - surfaced to user
            st.error(f"Failed to load file: {exc}")
            return

        register_stream(stream=loaded.stream, name=uploaded_file.name, summary=loaded.summary)
        st.success(f"Loaded file: {session.dataset_name}")
        with st.expander("Stream summary"):
            st.code(session.stream_summary or "No summary available", language="text")

    kelunji_location = session.metadata.get("kelunji_last")
    if kelunji_location:
        st.markdown("<div class='waveform-card'>", unsafe_allow_html=True)
        st.caption("Ubicación registrada (Kelunji)")
        columns = st.columns(3)
        columns[0].metric("Latitud", kelunji_location.get("lat", "—"))
        columns[1].metric("Longitud", kelunji_location.get("long", "—"))
        columns[2].metric("Altitud (m)", kelunji_location.get("alt", "—"))
        st.markdown("</div>", unsafe_allow_html=True)

    current_stream = get_current_stream(session)
    traces = _extract_traces(current_stream)

    st.markdown("<div class='waveform-card'>", unsafe_allow_html=True)

    if traces:
        labels = list_trace_labels(session=session, stream=traces)
        controls = render_waveform_sidebar(labels)
        selected_labels = controls.selected_stations or labels
        if selected_labels:
            active_trace = set_selected_trace(selected_labels[0], session=session)
        else:
            active_trace = None

        traces_to_plot = get_traces_by_labels(selected_labels, session=session) or traces

        # Picks existentes
        existing_picks = list_picks(session=session)
        fig = create_waveform_plot(
            traces_to_plot,
            controls.time_window,
            unit=controls.unit,
            picks=existing_picks,
            filter_type=controls.filter_type,
            freqmin=controls.freqmin,
            freqmax=controls.freqmax,
            amplitude_scale=controls.amplitude_scale,
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        with st.expander("Picks de Fase"):
            cols = st.columns([1,1,1,1])
            if cols[0].button("Limpiar picks"):
                clear_picks(session=session)
                st.rerun()
            if active_trace and cols[1].button("Añadir P (inicio ventana)"):
                start_time = controls.time_window[0]
                stats = getattr(active_trace, 'stats', None)
                add_pick(
                    phase='P',
                    time_rel=float(start_time),
                    station=getattr(stats, 'station', 'UNK'),
                    channel=getattr(stats, 'channel', 'CH'),
                    session=session,
                )
                st.rerun()
            if active_trace and cols[2].button("Añadir S (inicio ventana)"):
                start_time = controls.time_window[0]
                stats = getattr(active_trace, 'stats', None)
                add_pick(
                    phase='S',
                    time_rel=float(start_time),
                    station=getattr(stats, 'station', 'UNK'),
                    channel=getattr(stats, 'channel', 'CH'),
                    session=session,
                )
                st.rerun()
            suggest = cols[3].button("Sugerir (STA/LTA)")

            if suggest and active_trace:
                suggestions = suggest_picks_sta_lta(active_trace)
                if not suggestions:
                    st.info("Sin sugerencias STA/LTA.")
                else:
                    st.markdown("**Sugerencias (candidatos P?):**")
                    for s in suggestions:
                        c1, c2, c3 = st.columns([2,2,1])
                        c1.write(f"t = {s['time_rel']:.2f}s")
                        c2.write(f"score = {s['score']:.2f}")
                        if c3.button("+ Pick", key=f"pick_sugg_{s['time_rel']}"):
                            stats = getattr(active_trace, 'stats', None)
                            add_pick(
                                phase='P',
                                time_rel=float(s['time_rel']),
                                station=getattr(stats, 'station', 'UNK'),
                                channel=getattr(stats, 'channel', 'CH'),
                                session=session,
                            )
                            st.rerun()

            current_picks = list_picks(session=session)
            if current_picks:
                st.markdown("**Picks actuales:**")
                for i, p in enumerate(current_picks):
                    st.write(f"{i+1}. {p['phase']} | {p['station']}.{p['channel']} | t={p['time_rel']:.2f}s ({p['method']})")
                # If we have at least one P and one S for active trace station, attempt ML
                if active_trace is not None:
                    stats_active = getattr(active_trace, 'stats', None)
                    st_station = getattr(stats_active, 'station', 'UNK')
                    sr = float(getattr(stats_active, 'sampling_rate', 0) or 0)
                    if sr > 0:
                        import numpy as np
                        # Nuevo cálculo preliminar con aproximación Wood-Anderson
                        ml_result_wa = estimate_local_magnitude_wa(
                            picks=current_picks,
                            trace_data=np.asarray(active_trace.data),
                            trace_sampling_rate=sr,
                            station=st_station,
                        )
                        if ml_result_wa.ml is not None:
                            st.success(
                                f"ML (WA aprox) {ml_result_wa.ml:.2f} · ΔP-S {ml_result_wa.delta_ps:.2f}s · Dist~{ml_result_wa.distance_km:.1f} km"
                            )
                            if ml_result_wa.warnings:
                                with st.expander("Detalles ML / Advertencias"):
                                    for w in ml_result_wa.warnings:
                                        st.write(f"- {w}")
                        else:
                            st.caption(f"ML (WA aprox) no disponible: {ml_result_wa.notes}")
                        # Versión placeholder para comparar (opcional)
                        with st.expander("Comparar con versión placeholder (no rigurosa)"):
                            ml_old = estimate_local_magnitude(
                                picks=current_picks,
                                trace_data=np.asarray(active_trace.data),
                                trace_sampling_rate=sr,
                                station=st_station,
                            )
                            if ml_old.ml is not None:
                                st.write(f"ML placeholder: {ml_old.ml:.2f} (NO usar para análisis)")
                            else:
                                st.write(f"Placeholder no disponible: {ml_old.notes}")
                        st.caption("ML mostrado es preliminar. Requiere respuesta instrumental y localización multi-estación para ser publicable.")
            else:
                st.caption("No hay picks.")

        if active_trace is not None:
            st.caption(f"Trace seleccionada: {get_selected_trace_label(session)}")

        # Click events disabled for now due to compatibility issues with subplots
        # selected_points = capture_click_events(
        #     fig,
        #     key="waveform_viewer_plot",
        #     override_height=None,
        # )

        # if selected_points:
        #     st.write("Last pick:", selected_points[-1])
    else:
        st.info("No hay waveforms activos. Carga archivos desde la página 📁 Uploader.")

    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":  # pragma: no cover
    main()
