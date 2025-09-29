"""AI interpreter interface."""

from __future__ import annotations

import os
from numbers import Number
from pathlib import Path
from typing import List
from datetime import datetime, timedelta

import streamlit as st
from dotenv import load_dotenv

# Load environment variables
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=False)

from src.ai_agent.earthquake_search import EarthquakeQuery, EarthquakeSearcher
from src.ai_agent.report_generator import build_report_agent, generate_markdown_report, build_report_md
from src.ai_agent.seismic_interpreter import load_agent_suite, run_primary_analysis, run_team_analysis
from src.streamlit_utils.session_state import (
    get_current_stream_name,
    get_session,
    get_traces_by_labels,
    get_selected_trace_label,
    list_dataset_names,
    list_trace_labels,
    set_current_stream,
    get_team_context,
)
from src.utils.config import load_yaml
from src.utils.logger import setup_logger
from src.streamlit_utils.appearance import handle_error

LOGGER = setup_logger(__name__)


def _get_agent_suite():
    if "ai_agents" not in st.session_state:
        st.session_state["ai_agents"] = load_agent_suite()
    return st.session_state["ai_agents"]


def _pick_default_labels(session, labels: List[str]) -> List[str]:
    if not labels:
        return []

    stored = session.metadata.get("ai_selected_trace_labels")
    if isinstance(stored, list):
        preserved = [label for label in stored if label in labels]
        if preserved:
            return preserved

    preferred = get_selected_trace_label(session=session)
    if preferred and preferred in labels:
        return [preferred]

    return [labels[0]]


def _build_trace_context(session, labels: List[str]) -> str:
    base_summary = session.stream_summary or ""
    traces = get_traces_by_labels(labels, session=session)
    if not traces:
        return base_summary

    lines = ["Selected trace snapshots:"]
    for label, trace in zip(labels, traces):
        stats = getattr(trace, "stats", None)
        if not stats:
            lines.append(f"- {label}")
            continue

        station = getattr(stats, "station", "?")
        channel = getattr(stats, "channel", "?")
        npts = getattr(stats, "npts", "?")
        delta = getattr(stats, "delta", None)
        sampling_rate = getattr(stats, "sampling_rate", None)
        start = getattr(stats, "starttime", None)

        duration = None
        try:
            if isinstance(npts, Number) and isinstance(delta, Number):
                duration = float(str(npts)) * float(str(delta))
        except (ValueError, TypeError):
            duration = None

        parts = [f"station={station}", f"channel={channel}"]
        if sampling_rate:
            parts.append(f"fs={sampling_rate} Hz")
        elif delta:
            parts.append(f"Δ={delta} s")
        if duration:
            parts.append(f"duration≈{duration:.2f} s")
        parts.append(f"samples={npts}")
        if start:
            parts.append(f"start={start}")

        lines.append(f"- {label}: " + ", ".join(str(item) for item in parts if item))

    contextual = "\n".join(lines)
    if base_summary:
        return f"{base_summary}\n\n{contextual}"
    return contextual


def _parse_float(value) -> float | None:
    try:
        if value is None:
            return None
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _extract_waveform_date_range(session) -> tuple[datetime | None, datetime | None]:
    """Extrae el rango de fechas de los datos de waveform cargados."""
    try:
        from src.streamlit_utils.session_state import get_current_stream
        current_stream = get_current_stream(session)
        if not current_stream:
            return None, None
        
        start_times = []
        end_times = []
        
        for trace in current_stream:
            stats = getattr(trace, "stats", None)
            if not stats:
                continue
            
            start_time = getattr(stats, "starttime", None)
            end_time = getattr(stats, "endtime", None)
            
            if start_time:
                start_times.append(start_time.datetime)
            if end_time:
                end_times.append(end_time.datetime)
        
        if start_times and end_times:
            return min(start_times), max(end_times)
        
    except Exception:
        pass
    
    return None, None


def _kelunji_coordinates(session) -> tuple[float | None, float | None, float | None]:
    metadata = session.metadata.get("kelunji_last") if session else None
    if not isinstance(metadata, dict):
        return None, None, None
    return (
        _parse_float(metadata.get("lat")),
        _parse_float(metadata.get("long")),
        _parse_float(metadata.get("alt")),
    )


def main() -> None:
    st.header("🤖 AI Seismic Interpreter")
    session = get_session()

    if not session or not session.stream_summary:
        st.info("Upload and visualize a seismic dataset before running the AI interpreter.")
        return

    dataset_names = list_dataset_names(session=session)
    current_dataset = get_current_stream_name(session=session)
    if dataset_names:
        selected_dataset = st.selectbox(
            "Active dataset",
            options=dataset_names,
            index=dataset_names.index(current_dataset) if current_dataset in dataset_names else 0,
            key="ai_active_dataset",
        )
        if selected_dataset and selected_dataset != current_dataset:
            set_current_stream(selected_dataset, session=session)
            current_dataset = selected_dataset

    agents = _get_agent_suite()
    labels = list_trace_labels(session=session)
    if not labels:
        st.info("No active traces detected. Please review your dataset in the waveform viewer.")
        return

    default_labels = _pick_default_labels(session, labels)
    selected_labels = st.multiselect(
        "Choose traces for AI interpretation",
        options=labels,
        default=default_labels,
        help="Select one or more traces to enrich the AI prompt.",
    )

    if selected_labels:
        session.metadata["ai_selected_trace_labels"] = selected_labels
        st.caption(f"Dataset: {session.dataset_name or 'Unnamed dataset'}")
        preview = get_traces_by_labels(selected_labels, session=session)
        if preview:
            with st.expander("Selected trace stats", expanded=False):
                for label, trace in zip(selected_labels, preview):
                    st.markdown(f"**{label}**")
                    st.code(str(getattr(trace, "stats", trace)), language="text")
    else:
        st.warning("Select at least one trace to enable AI interpretation.")

    config = load_yaml("agno_config.yaml").get("seismic_interpreter", {})
    st.subheader("AI Analysis")

    # Opciones avanzadas (equipo IA) para incluir telemetría/histogramas previos
    with st.expander("Opciones avanzadas (Equipo IA)"):
        include_telemetry = st.checkbox(
            "Incluir telemetría/histogramas desde el contexto (página Histogramas)",
            value=False,
            help="Si está activo, el equipo IA considerará la vista previa y columnas enviadas desde la página de Histogramas.",
        )

    # Selección de modo de análisis: agente de waveform o equipo IA coordinado
    analysis_mode = st.radio(
        "Modo de análisis",
        options=["Agente de Waveform", "Equipo IA (coordinado)"],
        horizontal=True,
        help="Elige si deseas una interpretación rápida del agente de waveform o un análisis coordinado multi‑agente.",
    )

    if st.button("🚀 Run AI Interpretation", disabled=not selected_labels):
        prompt_summary = _build_trace_context(session, selected_labels)
        with st.spinner("Running AI agents..."):
            try:
                if analysis_mode == "Equipo IA (coordinado)":
                    # Contexto para equipo IA: waveform + opcionalmente telemetría + eq_search desde metadatos
                    telemetry_ctx = None
                    if include_telemetry:
                        team_ctx = get_team_context() or {}
                        telemetry_src = team_ctx.get("telemetry") or {}
                        if telemetry_src:
                            telemetry_ctx = {
                                "columns": telemetry_src.get("columns", []),
                                "df_head": telemetry_src.get("df_head", ""),
                                "notes": telemetry_src.get("notes"),
                                "meta": telemetry_src.get("meta", {}),
                                "filename": telemetry_src.get("filename"),
                                "analysis_ts": telemetry_src.get("analysis_ts"),
                                "params": telemetry_src.get("params"),
                            }

                    context = {
                        "time_range": None,
                        "telemetry": telemetry_ctx,
                        "waveform_summary": prompt_summary,
                        # Coordenadas persistidas para correlación sísmica
                        "eq_search": {
                            "latitude": session.metadata.get("earthquake_search_lat"),
                            "longitude": session.metadata.get("earthquake_search_lon"),
                            "radius_km": int(session.metadata.get("earthquake_search_radius_km", 100)),
                            "days": 30,
                            "min_magnitude": 2.5,
                        },
                        "location": None,
                    }
                    result = run_team_analysis(agents, context=context)
                    analysis = (result or {}).get("markdown")
                    session.ai_results["analysis"] = analysis
                else:
                    # Modo clásico: agente de waveform
                    analysis = run_primary_analysis(agents, prompt_summary)
                    session.ai_results["analysis"] = analysis
            except Exception as exc:
                handle_error(exc, context="Error en análisis IA")
                analysis = None
        if not analysis:
            st.warning("AI analysis not available. Check agent configuration.")

    if session.ai_results.get("analysis"):
        st.markdown(session.ai_results["analysis"])

    st.subheader("Earthquake Context")

    # Extraer rango de fechas de los waveforms
    waveform_start, waveform_end = _extract_waveform_date_range(session)
    if waveform_start and waveform_end:
        st.info(f"📅 Datos sísmicos: {waveform_start.strftime('%Y-%m-%d %H:%M')} → {waveform_end.strftime('%Y-%m-%d %H:%M')} UTC")
        # Calcular ventana de búsqueda alrededor de los datos
        search_days_before = st.slider(
            "Días antes de los datos", 
            min_value=1, max_value=30, value=7,
            help="Buscar eventos X días antes del inicio de los datos"
        )
        search_days_after = st.slider(
            "Días después de los datos", 
            min_value=1, max_value=30, value=7,
            help="Buscar eventos X días después del final de los datos"
        )
    else:
        st.warning("⚠️ No se pudo extraer fecha de los waveforms, usando fecha actual")
        search_days_before = 7
        search_days_after = 7

    kelunji_lat, kelunji_lon, kelunji_alt = _kelunji_coordinates(session)
    stored_lat = session.metadata.get("earthquake_search_lat") if session else None
    stored_lon = session.metadata.get("earthquake_search_lon") if session else None

    if stored_lat is None and kelunji_lat is not None:
        stored_lat = kelunji_lat
        session.metadata["earthquake_search_lat"] = stored_lat
    if stored_lon is None and kelunji_lon is not None:
        stored_lon = kelunji_lon
        session.metadata["earthquake_search_lon"] = stored_lon

    col1, col2 = st.columns(2)
    with col1:
        lat = st.number_input(
            "Latitude",
            value=float(stored_lat) if stored_lat is not None else 0.0,
            min_value=-90.0,
            max_value=90.0,
            format="%.5f",
        )
    with col2:
        lon = st.number_input(
            "Longitude",
            value=float(stored_lon) if stored_lon is not None else 0.0,
            min_value=-180.0,
            max_value=180.0,
            format="%.5f",
        )

    session.metadata["earthquake_search_lat"] = lat
    session.metadata["earthquake_search_lon"] = lon

    if kelunji_lat is not None and kelunji_lon is not None:
        st.caption("Coordenadas precargadas desde metadatos Kelunji. Ajusta si lo necesitas.")

    default_radius = session.metadata.get("earthquake_search_radius_km", 100)
    radius = st.slider(
        "Search radius (km)",
        min_value=10,
        max_value=500,
        value=int(default_radius) if isinstance(default_radius, (int, float)) else 100,
        step=10,
    )
    session.metadata["earthquake_search_radius_km"] = radius

    if st.button("🔍 Fetch Nearby Events"):
        try:
            searcher = EarthquakeSearcher(
                os.getenv("USGS_API_URL", "https://earthquake.usgs.gov/fdsnws/event/1/"),
                os.getenv("EMSC_API_URL", "https://www.seismicportal.eu/fdsnws/event/1/"),
            )
            
            # Usar fechas de waveforms si están disponibles
            if waveform_start and waveform_end:
                query_start = waveform_start - timedelta(days=search_days_before)
                query_end = waveform_end + timedelta(days=search_days_after)
                query = EarthquakeQuery(
                    latitude=lat, 
                    longitude=lon, 
                    radius_km=radius,
                    start=query_start,
                    end=query_end
                )
                st.info(f"Búsqueda: {query_start.strftime('%Y-%m-%d')} → {query_end.strftime('%Y-%m-%d')}")
            else:
                # Fallback: usar fecha actual con ventana estándar
                query = EarthquakeQuery(latitude=lat, longitude=lon, radius_km=radius)
                st.info("Búsqueda: últimos 30 días desde fecha actual")
            
            results = searcher.search_all(query)
            summary = searcher.summarize_results(results)
            session.ai_results["earthquakes"] = summary
            st.markdown(summary)
        except Exception as exc:
            handle_error(exc, context="Error al buscar eventos sísmicos")
    elif session.ai_results.get("earthquakes"):
        st.markdown(session.ai_results["earthquakes"])

    st.subheader("Automated Report")
    col1, col2 = st.columns([2, 1])
    with col1:
        if st.button("📝 Generate Report IA", disabled=not session.ai_results.get("analysis")):
            try:
                default_model = config.get("default_model", {})
                report_agent = build_report_agent(
                    default_model.get("provider", "openrouter"),
                    default_model.get("id", "deepseek/deepseek-chat-v3.1:free"),
                )
                report = generate_markdown_report(
                    report_agent,
                    waveform_summary=session.stream_summary,
                    ai_analysis=session.ai_results.get("analysis"),
                    earthquake_context=session.ai_results.get("earthquakes"),
                )
                session.ai_results["report"] = report
                st.download_button(
                    "⬇️ Download Markdown IA",
                    data=report,
                    file_name="seismic_report.md",
                    mime="text/markdown",
                )
                st.markdown(report)
            except Exception as exc:
                handle_error(exc, context="Error al generar reporte IA")
        elif session.ai_results.get("report"):
            st.download_button(
                "⬇️ Download Markdown IA",
                data=session.ai_results["report"],
                file_name="seismic_report.md",
                mime="text/markdown",
            )
            st.markdown(session.ai_results["report"])
    with col2:
        if st.button("📝 Exportar Reporte Institucional", disabled=not session.ai_results.get("analysis")):
            report_md = build_report_md(
                waveform_summary=session.stream_summary or "",
                ai_analysis=session.ai_results.get("analysis") or "",
                earthquake_context=session.ai_results.get("earthquakes") or "",
            )
            st.download_button(
                "⬇️ Descargar Reporte Institucional",
                data=report_md,
                file_name="reporte_institucional.md",
                mime="text/markdown",
            )
            st.markdown(report_md)


if __name__ == "__main__":  # pragma: no cover
    main()
