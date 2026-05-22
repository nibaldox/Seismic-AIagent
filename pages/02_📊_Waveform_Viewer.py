"""Waveform viewer page with integrated help system."""

from __future__ import annotations

from typing import Any, Iterable, List
from numbers import Number

import numpy as np
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
    mark_pipeline_step,
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
from src.ai_agent.seismic_interpreter import run_primary_analysis
from src.streamlit_utils.agent_loader import get_agent_suite as _get_agent_suite
from src.core.intensity_measures import compute_all_ims
from src.core.signal_processing import remove_baseline
from src.core.signal_qc import run_qc, qc_summary_markdown
from src.streamlit_utils.session_state import set_qc_results, get_qc_results


def _build_waveform_context(session, labels: List[str]) -> str:
    """Build a structured waveform context string for AI agents.

    Includes per-trace metadata plus basic signal metrics (PGA, RMS, rough SNR
    estimate, dominant frequency) so agents can reason about actual signal values
    rather than just file metadata.
    """
    import numpy as np

    base = session.stream_summary or ""
    traces = get_traces_by_labels(labels, session=session)

    # Collect existing picks for this session
    picks_list = list_picks(session=session)

    lines: List[str] = []
    for label, trace in zip(labels, traces):
        stats = getattr(trace, "stats", None)
        if not stats:
            lines.append(f"- {label}")
            continue

        station = getattr(stats, "station", "UNK")
        channel = getattr(stats, "channel", "CH")
        sampling_rate = float(getattr(stats, "sampling_rate", 0) or 0)
        delta = getattr(stats, "delta", None)
        npts = getattr(stats, "npts", None)
        start = getattr(stats, "starttime", None)

        duration = None
        if isinstance(npts, Number) and isinstance(delta, Number):
            duration = float(npts) * float(delta)

        parts = [f"station={station}", f"channel={channel}"]
        if sampling_rate:
            parts.append(f"fs={sampling_rate:.1f} Hz")
        elif delta:
            parts.append(f"delta={delta}")
        if duration is not None:
            parts.append(f"duration={duration:.1f}s")
        if isinstance(npts, Number):
            parts.append(f"samples={int(npts)}")
        if start:
            parts.append(f"start={start}")

        # --- Signal metrics ---
        data = getattr(trace, "data", None)
        if data is not None:
            try:
                arr = np.asarray(data, dtype=float)
                if arr.size > 10:
                    pga = float(np.max(np.abs(arr)))
                    rms = float(np.sqrt(np.mean(arr ** 2)))
                    parts.append(f"PGA={pga:.2f} counts")
                    parts.append(f"RMS={rms:.2f} counts")

                    # Rough SNR: compare last 10 % (assumed noise) to max amplitude
                    noise_len = max(1, arr.size // 10)
                    noise_rms = float(np.sqrt(np.mean(arr[-noise_len:] ** 2)))
                    if noise_rms > 0:
                        snr_db = 20.0 * np.log10(pga / noise_rms)
                        parts.append(f"SNR≈{snr_db:.1f} dB")

                    # Dominant frequency via FFT (skip DC bin)
                    if sampling_rate > 0:
                        win = np.hanning(arr.size)
                        spec = np.abs(np.fft.rfft(arr * win))
                        freqs = np.fft.rfftfreq(arr.size, d=1.0 / sampling_rate)
                        if spec.size > 1:
                            dom_idx = int(np.argmax(spec[1:])) + 1
                            parts.append(f"f_dom={freqs[dom_idx]:.2f} Hz")
            except Exception:
                pass  # métricas opcionales — no interrumpir flujo

        lines.append(f"- {label}: " + ", ".join(str(p) for p in parts if p))

    # Append picks summary
    if picks_list:
        lines.append("")
        lines.append("Picks registrados:")
        for pk in picks_list:
            p_station = pk.get("station", "?")
            p_channel = pk.get("channel", "?")
            p_phase = pk.get("phase", "?")
            p_time = pk.get("time_rel", "?")
            lines.append(f"  {p_phase} @ {p_time}s — {p_station}.{p_channel}")

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
            "Dataset activo",
            options=dataset_names,
            index=dataset_names.index(current_dataset) if current_dataset in dataset_names else 0,
            key="waveform_active_dataset",
        )
        if selected_dataset and selected_dataset != current_dataset:
            set_current_stream(selected_dataset, session=session)
            current_dataset = selected_dataset
        else:
            # Siempre intentar refrescar la caché al entrar a la página,
            # por si el stream se perdió tras hot-reload de Streamlit.
            set_current_stream(current_dataset or selected_dataset, session=session)

    uploaded_files = seismic_file_uploader("Subir archivos sísmicos", accept_multiple=False)
    if uploaded_files:
        uploaded_file = uploaded_files[0]
        with st.spinner("Cargando archivo sísmico..."):
            try:
                loaded = reader.load_bytes(buffer=uploaded_file, format_hint=None)
            except Exception as exc:
                handle_error(exc, context="Carga de archivo sísmico")
                return

            register_stream(stream=loaded.stream, name=uploaded_file.name, summary=loaded.summary)
            st.success(f"Cargado: {session.dataset_name}")
            with st.expander("Resumen del stream"):
                st.code(session.stream_summary or "Sin resumen disponible", language="text")

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
                            try:
                                ml_result_wa = estimate_local_magnitude_wa(
                                    picks=current_picks,
                                    trace_data=np.asarray(active_trace.data),
                                    trace_sampling_rate=sr,
                                    station=st_station,
                                )
                                if ml_result_wa.ml is not None:
                                    unc = ml_result_wa.ml_uncertainty
                                    unc_str = f" ± {unc:.1f}" if unc is not None else ""
                                    st.warning(
                                        f"**ML ≈ {ml_result_wa.ml:.1f}{unc_str}** (preliminar)  \n"
                                        f"ΔP-S {ml_result_wa.delta_ps:.2f}s · Dist≈{ml_result_wa.distance_km:.0f} km  \n"
                                        f"⚠️ Estimación de una sola estación sin respuesta instrumental corregida. "
                                        f"No publicar sin red multi-estación y calibración regional."
                                    )
                                    if ml_result_wa.warnings:
                                        with st.expander("Detalles del cálculo ML"):
                                            for warning in ml_result_wa.warnings:
                                                st.write(f"- {warning}")
                                else:
                                    st.caption(f"ML no disponible: {ml_result_wa.notes}")
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

            # ── Control de Calidad V1 ──────────────────────────────────────
            with st.expander("🔍 Control de Calidad de Señal (QC — V1)", expanded=False):
                st.caption(
                    "Evalúa la calidad del registro crudo (V0) antes de procesar. "
                    "Estándar COSMOS: detecta saturación, SNR bajo, gaps y deriva de baseline."
                )
                qc_col1, qc_col2 = st.columns([1, 1])
                run_qc_btn = qc_col1.button("Ejecutar QC en todas las trazas", key="run_qc_btn")
                ds_key = current_dataset or "unknown"

                if run_qc_btn:
                    qc_results_dict = {}
                    for lbl, tr in zip(selected_labels, traces_to_plot):
                        try:
                            result = run_qc(tr)
                            qc_results_dict[lbl] = {
                                "verdict": result.verdict,
                                "snr_db": result.snr_db,
                                "clip_ratio": result.clip_ratio,
                                "n_gaps": result.n_gaps,
                                "drift_pct": result.drift_magnitude_pct,
                                "duration_s": result.duration_s,
                                "reasons": result.reasons,
                                "markdown": qc_summary_markdown(result),
                            }
                        except Exception as exc:
                            qc_results_dict[lbl] = {"verdict": "ERROR", "error": str(exc)}
                    set_qc_results(ds_key, qc_results_dict, session=session)
                    mark_pipeline_step("V1_qc", session=session)
                    st.rerun()

                saved_qc = get_qc_results(ds_key, session=session)
                if saved_qc:
                    _VERDICT_COLORS = {
                        "ACEPTADO": "🟢", "CONDICIONADO": "🟡", "RECHAZADO": "🔴",
                    }
                    import pandas as _pd
                    rows = []
                    for lbl, qc in saved_qc.items():
                        if qc.get("verdict") == "ERROR":
                            rows.append({"Traza": lbl, "Veredicto": "❌ ERROR",
                                         "SNR (dB)": "—", "Sat %": "—", "Gaps": "—", "Drift %": "—"})
                        else:
                            rows.append({
                                "Traza": lbl,
                                "Veredicto": f"{_VERDICT_COLORS.get(qc['verdict'], '⚪')} {qc['verdict']}",
                                "SNR (dB)": f"{qc['snr_db']:.1f}",
                                "Sat %": f"{qc['clip_ratio']*100:.2f}",
                                "Gaps": str(qc["n_gaps"]),
                                "Drift %": f"{qc['drift_pct']:.1f}",
                            })
                    st.dataframe(_pd.DataFrame(rows).set_index("Traza"), use_container_width=True)

                    with st.expander("Ver detalles por traza", expanded=False):
                        for lbl, qc in saved_qc.items():
                            if md := qc.get("markdown"):
                                st.markdown(md)
                            elif err := qc.get("error"):
                                st.error(f"{lbl}: {err}")
                else:
                    st.info("Haz clic en **Ejecutar QC** para evaluar la calidad de las trazas cargadas.")

            # ── Corrección de línea de base ────────────────────────────────
            with st.expander("🔧 Corrección de Línea de Base (Baseline — V1)", expanded=False):
                st.caption(
                    "Paso V1 estándar COSMOS: elimina deriva DC antes de integrar "
                    "para obtener velocidad y desplazamiento precisos."
                )
                bc_method = st.selectbox(
                    "Método",
                    options=["linear", "mean", "polynomial"],
                    format_func=lambda x: {
                        "mean": "Orden 0 — resta media",
                        "linear": "Orden 1 — tendencia lineal (recomendado)",
                        "polynomial": "Orden 2 — polinomial cuadrática",
                    }[x],
                    index=0,
                    key="bc_method",
                )
                poly_order = 2
                if bc_method == "polynomial":
                    poly_order = st.slider("Orden polinomio", 2, 4, 2, key="bc_poly_order")

                # ── Preview antes/después ──────────────────────────────────
                if active_trace is not None:
                    try:
                        import plotly.graph_objects as _go_bc
                        orig = np.asarray(active_trace.data, dtype=float)
                        preview = remove_baseline(orig, method=bc_method, poly_order=poly_order)
                        dt_bc = float(active_trace.stats.delta)
                        t_bc  = np.arange(len(orig)) * dt_bc
                        fig_bc = _go_bc.Figure()
                        fig_bc.add_trace(_go_bc.Scatter(
                            x=t_bc, y=orig, mode="lines", name="Original",
                            line=dict(color="#636e72", width=1),
                        ))
                        fig_bc.add_trace(_go_bc.Scatter(
                            x=t_bc, y=preview, mode="lines", name="Corregida",
                            line=dict(color="#55efc4", width=1.5),
                        ))
                        fig_bc.update_layout(
                            template="plotly_dark",
                            xaxis_title="Tiempo (s)", yaxis_title="Amplitud",
                            height=220, margin=dict(t=10, b=30, l=40, r=10),
                            legend=dict(x=0.01, y=0.99),
                            hovermode="x unified",
                        )
                        st.plotly_chart(fig_bc, use_container_width=True, key="bc_preview_chart")
                    except Exception:
                        pass

                apply_bc = st.button("Aplicar corrección al trace activo", key="apply_baseline")
                if apply_bc and active_trace is not None:
                    try:
                        corrected = remove_baseline(
                            np.asarray(active_trace.data, dtype=float),
                            method=bc_method,
                            poly_order=poly_order,
                        )
                        active_trace.data = corrected
                        # Regenerar el stream en caché con la traza corregida
                        clear_trace_cache(session=session)
                        mark_pipeline_step("V1_filtered", session=session)
                        st.success("Corrección aplicada.")
                        st.rerun()
                    except Exception as exc:
                        handle_error(exc, context="Baseline correction")

            # ── Parámetros de Intensidad Sísmica (IMs) ────────────────────
            with st.expander("📊 Parámetros de Intensidad Sísmica (IMs)", expanded=True):
                if active_trace is not None:
                    import pandas as pd

                    # Calcular IMs para todas las trazas seleccionadas
                    all_im_rows = []
                    for lbl, tr in zip(selected_labels, traces_to_plot):
                        try:
                            ims = compute_all_ims(tr)
                            row = {"Traza": lbl}
                            row.update({
                                k: (f"{v:.4g}" if v is not None else "—")
                                for k, v in ims.to_dict().items()
                            })
                            all_im_rows.append(row)
                            if ims.warnings:
                                for w in ims.warnings:
                                    st.caption(f"⚠️ {lbl}: {w}")
                        except Exception as exc:
                            st.caption(f"Error calculando IMs para {lbl}: {exc}")

                    if all_im_rows:
                        mark_pipeline_step("V2_ims", session=session)
                        df_ims = pd.DataFrame(all_im_rows).set_index("Traza")
                        st.dataframe(df_ims.T, use_container_width=True)

                        # Botón de exportación a Excel
                        try:
                            import io
                            buf = io.BytesIO()
                            df_ims.T.to_excel(buf, sheet_name="IMs")
                            st.download_button(
                                "⬇️ Exportar IMs a Excel",
                                data=buf.getvalue(),
                                file_name=f"IMs_{session.dataset_name or 'dataset'}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key="dl_ims_excel",
                            )
                        except ImportError:
                            st.caption("Instala `openpyxl` para exportar a Excel.")
                    else:
                        st.info("No se pudieron calcular IMs para las trazas seleccionadas.")
                else:
                    st.info("Selecciona una traza para calcular los parámetros de intensidad.")

        with col_ai:
            st.subheader("Interprete IA")
            agents = _get_agent_suite()
            agent_error = st.session_state.get("ai_agents_error")
            if not agents:
                if agent_error:
                    st.error(f"No se pudo inicializar el interprete: {agent_error}")
                else:
                    st.info("Configura los agentes IA en config/agents_config.yaml.")
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
        if dataset_names:
            # Hay datasets registrados en sesión pero el stream no está en la caché
            # en memoria (ocurre tras hot-reload de Streamlit). El usuario debe volver
            # a cargar los datos desde la página original.
            st.warning(
                f"El dataset **`{current_dataset}`** está registrado en la sesión "
                "pero sus datos no están disponibles en memoria. "
                "Esto ocurre cuando Streamlit se recarga. "
                "Ve a **Batch Loader** (pág. 01) o **Uploader** (pág. 00) y vuelve a cargar los archivos."
            )
        else:
            st.info("No hay waveforms activos. Carga archivos desde **Uploader** (pág. 00) o **Batch Loader** (pág. 01).")

        st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":  # pragma: no cover
    main()
