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
from src.ai_agent.report_generator import (
    build_report_agent,
    generate_markdown_report,
    build_report_md,
    generate_html_report,
)
from src.ai_agent.seismic_interpreter import run_primary_analysis, run_team_analysis
from src.streamlit_utils.agent_loader import get_agent_suite as _get_agent_suite_central
from src.streamlit_utils.session_state import (
    get_current_stream_name,
    get_session,
    get_traces_by_labels,
    get_selected_trace_label,
    list_dataset_names,
    list_trace_labels,
    set_current_stream,
    get_team_context,
    list_ai_history,
)
from src.utils.config import load_yaml
from src.utils.logger import setup_logger
from src.streamlit_utils.appearance import handle_error

LOGGER = setup_logger(__name__)


def _get_agent_suite():
    return _get_agent_suite_central()


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
    
    # Mostrar modelo activo
    current_model = st.session_state.get("selected_ai_model", "nvidia/nemotron-3-super-120b-a12b:free")
    model_display_names = {
        "nvidia/nemotron-3-super-120b-a12b:free": "NVIDIA Nemotron Super 120B",
        "moonshotai/kimi-k2:free": "Moonshot Kimi K2",
        "x-ai/grok-4-fast:free": "xAI Grok 4 Fast",
        "meituan/longcat-flash-chat": "Meituan LongCat Flash",
        "z-ai/glm-4.5-air:free": "Z-AI GLM 4.5 Air",
        "qwen/qwen3-235b-a22b:free": "Qwen3 235B (non-thinking)",
        "deepseek/deepseek-chat-v3.1:free": "DeepSeek Chat v3.1 (no disponible)",
    }
    if current_model.startswith("lmstudio:"):
        lm_name = current_model[len("lmstudio:"):]
        lm_url = st.session_state.get("lmstudio_base_url", "http://127.0.0.1:1234/v1")
        display = f"🖥️ LM Studio — {lm_name} · {lm_url}"
    else:
        display = model_display_names.get(current_model, current_model)
    st.info(f"🤖 Modelo activo: **{display}**")

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

    # Extraer rango de fechas ANTES del botón para usarlo en el contexto del equipo
    _wf_start_pre, _wf_end_pre = _extract_waveform_date_range(session)

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

                    # Construir time_range desde los waveforms cargados
                    time_range_str = None
                    if _wf_start_pre and _wf_end_pre:
                        time_range_str = (
                            f"{_wf_start_pre.strftime('%Y-%m-%d %H:%M:%S')} UTC → "
                            f"{_wf_end_pre.strftime('%Y-%m-%d %H:%M:%S')} UTC"
                        )

                    # Picks P/S disponibles en sesión
                    from src.streamlit_utils.session_state import list_picks
                    current_picks = list_picks(session=session) or []
                    picks_summary = None
                    if current_picks:
                        picks_lines = [
                            f"  - {p.get('phase','?')} @ {p.get('station','?')} "
                            f"t_rel={float(p.get('time_rel',0)):.3f}s "
                            f"método={p.get('method','?')}"
                            for p in current_picks
                        ]
                        picks_summary = "Picks P/S disponibles:\n" + "\n".join(picks_lines)

                    # ── Contexto HVSR ────────────────────────────────────
                    hvsr_ctx = None
                    _hv = st.session_state.get("hvsr_result")
                    if _hv is not None:
                        hvsr_ctx = {
                            "f0_hz": round(_hv.f0_hz, 3),
                            "T0_s":  round(_hv.t0_s, 3),
                            "amplitude": round(_hv.a0, 2),
                            "n_windows": _hv.n_windows,
                            "sesame_valid": _hv.sesame.all_passed,
                            "sesame_summary": _hv.sesame.summary,
                        }

                    # ── Contexto RotD50 ──────────────────────────────────
                    rotd_ctx = None
                    _rd = st.session_state.get("rotd_result")
                    if _rd is not None:
                        try:
                            import numpy as _np_rd
                            rotd_ctx = {
                                "comp1": _rd.comp1_id,
                                "comp2": _rd.comp2_id,
                                "damping_pct": round(_rd.damping * 100, 0),
                                "rotd50_max_cms2": round(float(_np_rd.max(_rd.rotd50)), 2),
                                "rotd100_max_cms2": round(float(_np_rd.max(_rd.rotd100)), 2),
                                "T_at_rotd50_max_s": round(
                                    float(_rd.periods[_np_rd.argmax(_rd.rotd50)]), 3
                                ),
                            }
                        except Exception:
                            pass

                    context = {
                        "time_range": time_range_str,
                        "analysis_ts": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                        "telemetry": telemetry_ctx,
                        "waveform_summary": prompt_summary,
                        "picks": picks_summary,
                        "hvsr": hvsr_ctx,
                        "rotd50": rotd_ctx,
                        # Coordenadas persistidas para correlación sísmica
                        "eq_search": {
                            "latitude": session.metadata.get("earthquake_search_lat"),
                            "longitude": session.metadata.get("earthquake_search_lon"),
                            "radius_km": int(session.metadata.get("earthquake_search_radius_km", 100)),
                            "days": int(session.metadata.get("earthquake_search_days", 30)),
                            "min_magnitude": float(session.metadata.get("earthquake_search_min_mag", 2.5)),
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

    # ── Historial IA ───────────────────────────────────────────────────────
    with st.expander("📜 Historial de análisis IA", expanded=False):
        st.caption("Compará análisis anteriores sin necesidad de volver a correr los agentes.")
        history = list_ai_history(session=session)
        if not history:
            st.info("Sin análisis previos en esta sesión.")
        else:
            for i, entry in enumerate(history):
                ts = entry.get("timestamp", "—")
                key = entry.get("key", "—")
                agent = entry.get("agent", "—")
                model = entry.get("model", "—")
                dur = entry.get("duration_s")
                content = entry.get("content", "")
                # Mostrar solo las primeras 300 chars del contenido
                preview = content[:300] + ("…" if len(content) > 300 else "")
                with st.container():
                    cols_h = st.columns([1, 1, 1, 1])
                    cols_h[0].caption(f"**{key}**")
                    cols_h[1].caption(f"{ts[11:19]}")  # HH:MM:SS
                    cols_h[2].caption(f"{agent}")
                    cols_h[3].caption(f"{model or '—'}")
                    st.markdown(preview)
                    st.divider()

    st.subheader("Earthquake Context")

    # Reutilizar el rango de fechas ya extraído antes del botón
    waveform_start, waveform_end = _wf_start_pre, _wf_end_pre
    if waveform_start and waveform_end:
        waveform_duration_h = (waveform_end - waveform_start).total_seconds() / 3600.0
        st.info(
            f"📅 Datos sísmicos: {waveform_start.strftime('%Y-%m-%d %H:%M')} → "
            f"{waveform_end.strftime('%Y-%m-%d %H:%M')} UTC "
            f"({waveform_duration_h:.1f} h)"
        )
        # Para trazas cortas (<6 h) usar horas como unidad para no buscar en
        # ventanas irrelevantemente largas (foreshocks/réplicas están en ±horas).
        if waveform_duration_h < 6.0:
            st.caption("Traza corta — ventana de búsqueda en horas (réplicas/precursores).")
            search_hours_before = st.slider(
                "Horas antes de los datos",
                min_value=1, max_value=72, value=6,
                help="Buscar eventos hasta X horas antes del inicio de los datos"
            )
            search_hours_after = st.slider(
                "Horas después de los datos",
                min_value=1, max_value=72, value=6,
                help="Buscar eventos hasta X horas después del final de los datos"
            )
            search_days_before = search_hours_before / 24.0
            search_days_after = search_hours_after / 24.0
        else:
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
        # Persistir en sesión para que el equipo IA los use
        session.metadata["earthquake_search_days"] = int(search_days_before + search_days_after)
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

    default_min_mag = session.metadata.get("earthquake_search_min_mag", 2.5)
    min_mag = st.slider(
        "Magnitud mínima",
        min_value=0.0,
        max_value=7.0,
        value=float(default_min_mag),
        step=0.5,
    )
    session.metadata["earthquake_search_min_mag"] = min_mag

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
                    end=query_end,
                    min_magnitude=min_mag,
                )
                st.info(f"Búsqueda: {query_start.strftime('%Y-%m-%d')} → {query_end.strftime('%Y-%m-%d')} | M≥{min_mag}")
            else:
                # Fallback: usar fecha actual con ventana estándar
                query = EarthquakeQuery(latitude=lat, longitude=lon, radius_km=radius, min_magnitude=min_mag)
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

    has_analysis = bool(session.ai_results.get("analysis"))

    col_html, col_md = st.columns([3, 2])

    with col_html:
        if st.button("📊 Exportar Informe HTML (con gráficos)", disabled=not has_analysis):
            with st.spinner("Generando informe HTML con gráficos..."):
                try:
                    from src.streamlit_utils.session_state import get_current_stream, list_picks
                    from src.visualization.waveform_plots import create_waveform_plot
                    from src.visualization.spectrum_plots import (
                        create_spectrogram,
                        create_fft_plot,
                        create_psd_plot,
                    )

                    current_stream = get_current_stream(session)
                    waveform_fig = None
                    spectrum_figs: dict = {}

                    if current_stream and len(current_stream) > 0:
                        try:
                            waveform_fig = create_waveform_plot(current_stream)
                        except Exception:
                            waveform_fig = None

                        first_trace = current_stream[0]
                        try:
                            spectrum_figs["Espectrograma"] = create_spectrogram(first_trace)
                        except Exception:
                            pass
                        try:
                            spectrum_figs["FFT"] = create_fft_plot(first_trace)
                        except Exception:
                            pass
                        try:
                            spectrum_figs["PSD"] = create_psd_plot(first_trace)
                        except Exception:
                            pass

                    html_report = generate_html_report(
                        dataset_name=session.dataset_name or "Dataset Sísmico",
                        stream_summary=session.stream_summary,
                        ai_analysis=session.ai_results.get("analysis"),
                        earthquake_context=session.ai_results.get("earthquakes"),
                        picks=list_picks(session=session),
                        waveform_fig=waveform_fig,
                        spectrum_figs=spectrum_figs or None,
                    )
                    session.ai_results["html_report"] = html_report
                except Exception as exc:
                    handle_error(exc, context="Error al generar informe HTML")

        if session.ai_results.get("html_report"):
            st.download_button(
                "⬇️ Descargar Informe HTML",
                data=session.ai_results["html_report"],
                file_name="informe_sismico.html",
                mime="text/html",
                key="dl_html_report",
            )
            st.success("Informe HTML listo para descargar.")

    with col_md:
        if st.button("📝 Generate Report IA (Markdown)", disabled=not has_analysis):
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
            except Exception as exc:
                handle_error(exc, context="Error al generar reporte IA")

        if session.ai_results.get("report"):
            st.download_button(
                "⬇️ Download Markdown IA",
                data=session.ai_results["report"],
                file_name="seismic_report.md",
                mime="text/markdown",
                key="dl_md_report",
            )
            with st.expander("Vista previa Markdown", expanded=False):
                st.markdown(session.ai_results["report"])


if __name__ == "__main__":  # pragma: no cover
    main()
