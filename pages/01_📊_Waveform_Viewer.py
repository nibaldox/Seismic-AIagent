"""Waveform viewer page with integrated help system."""

from __future__ import annotations

from typing import Any, Iterable, List
from numbers import Number

import streamlit as st
import sys
import os

# Agregar el directorio src al path para importaciones
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

# Importar sistema de ayuda
try:
    from streamlit_utils.help_system import show_help, show_quick_help
except ImportError:
    # Fallback si no se puede importar
    def show_help(page_key, expanded=False):
        pass
    def show_quick_help():
        pass

from src.core.data_reader import DataReader
from src.streamlit_utils.file_uploader import seismic_file_uploader
from src.streamlit_utils.plot_interactions import capture_click_events
from src.streamlit_utils.appearance import handle_error
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
    set_trace_cache,
    get_trace_cache,
    clear_trace_cache,
)
from src.streamlit_utils.sidebar_controls import render_waveform_sidebar
from src.visualization.waveform_plots import create_waveform_plot
from src.core.picking import suggest_picks_sta_lta, Pick, PickManager
from src.streamlit_utils.session_state import add_pick, list_picks, clear_picks
from src.core.magnitude import (
    estimate_local_magnitude,  # placeholder (mantener compatibilidad)
    estimate_local_magnitude_wa,
)
from src.ai_agent.seismic_interpreter import load_agent_suite, run_primary_analysis


def _get_agent_suite():
    if "ai_agents" in st.session_state:
        return st.session_state["ai_agents"]
    try:
        agents = load_agent_suite()
        st.session_state["ai_agents"] = agents
        st.session_state.pop("ai_agents_error", None)
        return agents
    except Exception as exc:
        st.session_state["ai_agents_error"] = str(exc)
        st.session_state["ai_agents"] = {}
        return {}


def _build_waveform_context(session, labels: List[str]) -> str:
    base = session.stream_summary or ""
    traces = get_traces_by_labels(labels, session=session)
    lines: List[str] = []
    for label, trace in zip(labels, traces):
        stats = getattr(trace, "stats", None)
        if not stats:
            lines.append(f"- {label}")
            continue
        station = getattr(stats, "station", "UNK")
        channel = getattr(stats, "channel", "CH")
        sampling_rate = getattr(stats, "sampling_rate", None)
        delta = getattr(stats, "delta", None)
        npts = getattr(stats, "npts", None)
        start = getattr(stats, "starttime", None)
        duration = None
        if isinstance(npts, Number) and isinstance(delta, Number):
            duration = float(npts) * float(delta)
        parts = [f"station={station}", f"channel={channel}"]
        if sampling_rate:
            parts.append(f"fs={sampling_rate}")
        elif delta:
            parts.append(f"delta={delta}")
        if duration is not None:
            parts.append(f"duration={duration:.2f}s")
        if isinstance(npts, Number):
            parts.append(f"samples={int(npts)}")
        if start:
            parts.append(f"start={start}")
        lines.append(f"- {label}: " + ", ".join(str(p) for p in parts if p))
    detail = "\n".join(lines)
    if base and detail:
        return f"{base}\n\n{detail}"
    return base or detail



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
    
    # Mostrar ayuda contextual
    try:
        show_help("waveform", expanded=False)
    except:
        pass  # Si no se puede mostrar ayuda, continuar sin ella
    
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
        with st.spinner("Cargando archivo sísmico..."):
            try:
                loaded = reader.load_bytes(buffer=uploaded_file, format_hint=None)
            except Exception as exc:
                handle_error(exc, context="Carga de archivo sísmico")
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

        # Construir clave de caché según dataset, ventana, filtros y etiquetas
        cache_key = f"{current_dataset}|{selected_labels}|{controls.time_window}|{controls.unit}|{controls.filter_type}|{controls.freqmin}|{controls.freqmax}"
        traces_to_plot = get_trace_cache(cache_key, session=session)
        if traces_to_plot is None:
            traces_to_plot = get_traces_by_labels(selected_labels, session=session) or traces
            set_trace_cache(cache_key, traces_to_plot, session=session)
        existing_picks = list_picks(session=session)

        # Invalidar caché si cambia el dataset
        if st.session_state.get("waveform_last_dataset") != current_dataset:
            clear_trace_cache(session=session)
            st.session_state["waveform_last_dataset"] = current_dataset
        col_plot, col_ai = st.columns([3, 2])

        with col_plot:
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
                cols = st.columns([1, 1, 1, 1])
                if cols[0].button("Limpiar picks"):
                    clear_picks(session=session)
                    st.rerun()
                if active_trace and cols[1].button("Anadir P (inicio ventana)"):
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
                if active_trace and cols[2].button("Anadir S (inicio ventana)"):
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
                    try:
                        suggestions = suggest_picks_sta_lta(active_trace)
                    except Exception as exc:
                        handle_error(exc, context="Sugerencia picks STA/LTA")
                        suggestions = []
                    if not suggestions:
                        st.info("Sin sugerencias STA/LTA.")
                    else:
                        st.markdown("**Sugerencias (candidatos P?):**")
                        for s in suggestions:
                            c1, c2, c3 = st.columns([2, 2, 1])
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
                    for idx, pick in enumerate(current_picks, start=1):
                        st.write(f"{idx}. {pick['phase']} | {pick['station']}.{pick['channel']} | t={pick['time_rel']:.2f}s ({pick['method']})")
                    if active_trace is not None:
                        stats_active = getattr(active_trace, 'stats', None)
                        st_station = getattr(stats_active, 'station', 'UNK')
                        sr = float(getattr(stats_active, 'sampling_rate', 0) or 0)
                        if sr > 0:
                            import numpy as np
                            try:
                                ml_result_wa = estimate_local_magnitude_wa(
                                    picks=current_picks,
                                    trace_data=np.asarray(active_trace.data),
                                    trace_sampling_rate=sr,
                                    station=st_station,
                                )
                                if ml_result_wa.ml is not None:
                                    st.success(
                                        f"ML (WA aprox) {ml_result_wa.ml:.2f} - DeltaP-S {ml_result_wa.delta_ps:.2f}s - Dist~{ml_result_wa.distance_km:.1f} km"
                                    )
                                    if ml_result_wa.warnings:
                                        with st.expander("Detalles ML / Advertencias"):
                                            for warning in ml_result_wa.warnings:
                                                st.write(f"- {warning}")
                                else:
                                    st.caption(f"ML (WA aprox) no disponible: {ml_result_wa.notes}")
                            except Exception as exc:
                                handle_error(exc, context="Estimación ML WA")

                            with st.expander("Comparar con version placeholder (no rigurosa)"):
                                try:
                                    ml_old = estimate_local_magnitude(
                                        picks=current_picks,
                                        trace_data=np.asarray(active_trace.data),
                                        trace_sampling_rate=sr,
                                        station=st_station,
                                    )
                                    if ml_old.ml is not None:
                                        st.write(f"ML placeholder: {ml_old.ml:.2f} (NO usar para analisis)")
                                    else:
                                        st.write(f"Placeholder no disponible: {ml_old.notes}")
                                except Exception as exc:
                                    handle_error(exc, context="Estimación ML placeholder")
                            st.caption("ML mostrado es preliminar. Requiere respuesta instrumental y localizacion multi-estacion para publicar.")
                else:
                    st.caption("No hay picks.")

            if active_trace is not None:
                st.caption(f"Trace seleccionada: {get_selected_trace_label(session)}")

        with col_ai:
            st.subheader("Interprete IA")
            agents = _get_agent_suite()
            agent_error = st.session_state.get("ai_agents_error")
            if not agents:
                if agent_error:
                    st.error(f"No se pudo inicializar el interprete: {agent_error}")
                else:
                    st.info("Configura los agentes IA en config/agno_config.yaml.")
            else:
                summary_text = _build_waveform_context(session, selected_labels)
                if not summary_text:
                    st.info("Selecciona al menos una traza para ejecutar el interprete IA.")
                else:
                    dataset_id = session.dataset_name or current_dataset or "dataset"
                    context_signature = f"{dataset_id}|{','.join(selected_labels)}"
                    context_key = "waveform_ai_context"
                    done_key = "waveform_ai_auto_done"
                    result_key = "waveform_ai_result"
                    if st.session_state.get(context_key) != context_signature:
                        st.session_state[context_key] = context_signature
                        st.session_state[done_key] = False
                        st.session_state.pop(result_key, None)
                        session.ai_results.pop("waveform_analysis", None)
                    run_requested = False
                    if not st.session_state.get(done_key, False):
                        run_requested = True
                    if st.button("Actualizar analisis IA", key="waveform_ai_run"):
                        run_requested = True
                        st.session_state[done_key] = False
                    if run_requested:
                        with st.spinner("Consultando interprete..."):
                            try:
                                analysis = run_primary_analysis(agents, summary_text)
                            except Exception as exc:
                                handle_error(exc, context="Análisis IA en Waveform")
                                analysis = None
                        if analysis:
                            session.ai_results["waveform_analysis"] = analysis
                            st.session_state[result_key] = analysis
                        else:
                            st.warning("No se recibio respuesta del agente.")
                            st.session_state[result_key] = None
                        st.session_state[done_key] = True
                    current_analysis = st.session_state.get(result_key) or session.ai_results.get("waveform_analysis")
                    if current_analysis:
                        st.markdown(current_analysis)
                    else:
                        st.info("El interprete IA aun no tiene resultados para este dataset.")
    else:
        st.info("No hay waveforms activos. Carga archivos desde la pagina 📁 Uploader.")

        st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":  # pragma: no cover
    main()
