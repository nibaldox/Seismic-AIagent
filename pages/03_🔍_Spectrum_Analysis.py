"""Spectral analysis page with AI interpretation and integrated help."""

from __future__ import annotations

import streamlit as st

# Importar sistema de ayuda
try:
    from src.streamlit_utils.help_system import show_help, show_quick_help
except ImportError:
    # Fallback si no se puede importar
    def show_help(page_key, expanded=False):
        pass
    def show_quick_help():
        pass

from src.streamlit_utils.session_state import (
    get_current_stream,
    get_current_stream_name,
    get_selected_trace,
    get_selected_trace_label,
    get_session,
    list_dataset_names,
    list_trace_labels,
    mark_pipeline_step,
    set_current_stream,
    set_selected_trace,
    get_traces_by_labels,
    set_spectral_cache,
    get_spectral_cache,
)
from src.streamlit_utils.appearance import handle_error
from src.visualization.spectrum_plots import create_spectrogram, create_fft_plot, create_psd_plot, create_hvsr_plot
from src.ai_agent.seismic_interpreter import run_spectrum_analysis
from src.streamlit_utils.agent_loader import get_agent_suite as _get_agent_suite
from src.core.design_spectra import (
    ncch433_spectrum, asce7_spectrum,
    NCH433_ZONES, NCH433_SOILS, ASCE7_SITE_CLASSES,
)
from src.core.intensity_measures import compute_all_ims
from src.core.rotd50 import compute_rotd
from src.core.hvsr import compute_hvsr

st.set_page_config(page_title="Spectrum Analysis", page_icon="🔍")


def _build_trace_context(trace, analysis_type: str, analysis_params: dict) -> tuple[dict, dict]:
    """Build an enriched context dict for AI analysis of spectral data.

    Includes per-trace signal metrics (PGA, RMS, SNR, dominant frequency) so
    agents receive actual numeric data rather than just file metadata.
    Serialisation errors are caught per-field so one bad value never silently
    wipes all context.
    """
    import numpy as np
    from scipy import signal as _signal

    def _safe(value):
        if value is None:
            return None
        if hasattr(value, 'isoformat'):
            return value.isoformat()
        if isinstance(value, (np.integer, np.floating)):
            return float(value)
        if isinstance(value, np.ndarray):
            return value.tolist()
        return str(value)

    trace_info: dict = {}

    if hasattr(trace, 'stats'):
        stats = trace.stats
        sr = float(getattr(stats, 'sampling_rate', 0) or 0)
        npts = int(getattr(stats, 'npts', 0) or 0)
        delta = float(getattr(stats, 'delta', 0) or 0)

        trace_info['station'] = _safe(getattr(stats, 'station', 'UNK'))
        trace_info['channel'] = _safe(getattr(stats, 'channel', 'CH'))
        trace_info['sampling_rate_hz'] = sr
        trace_info['npts'] = npts
        trace_info['duration_s'] = round(delta * npts, 2) if delta and npts else None
        trace_info['start_time'] = _safe(getattr(stats, 'starttime', None))
        trace_info['end_time'] = _safe(getattr(stats, 'endtime', None))

    # --- Signal metrics (computed directly from data) ---
    if hasattr(trace, 'data'):
        try:
            arr = np.asarray(trace.data, dtype=float)
            sr = float(getattr(getattr(trace, 'stats', None), 'sampling_rate', 0) or 1)
            if arr.size > 10:
                pga = float(np.max(np.abs(arr)))
                rms = float(np.sqrt(np.mean(arr ** 2)))
                trace_info['pga_counts'] = round(pga, 4)
                trace_info['rms_counts'] = round(rms, 4)

                # SNR: last 10 % of trace assumed noise
                noise_len = max(1, arr.size // 10)
                noise_rms = float(np.sqrt(np.mean(arr[-noise_len:] ** 2)))
                if noise_rms > 0:
                    trace_info['snr_db'] = round(20.0 * np.log10(pga / noise_rms), 1)

                # Dominant frequency
                if sr > 0:
                    win = np.hanning(arr.size)
                    spec = np.abs(np.fft.rfft((arr - arr.mean()) * win))
                    freqs = np.fft.rfftfreq(arr.size, d=1.0 / sr)
                    if spec.size > 1:
                        dom_idx = int(np.argmax(spec[1:])) + 1
                        trace_info['dominant_frequency_hz'] = round(float(freqs[dom_idx]), 3)

                # Spectral centroid and bandwidth from Welch PSD
                try:
                    nperseg_ctx = min(512, arr.size)
                    f_w, p_w = _signal.welch(arr, fs=sr, nperseg=nperseg_ctx,
                                             window='hann', detrend='linear')
                    if p_w.sum() > 0:
                        centroid = float(np.average(f_w, weights=p_w))
                        trace_info['spectral_centroid_hz'] = round(centroid, 3)
                        # Bandwidth: frequency range containing 80% of power
                        cumpower = np.cumsum(p_w) / p_w.sum()
                        f_lo = float(f_w[np.searchsorted(cumpower, 0.1)])
                        f_hi = float(f_w[np.searchsorted(cumpower, 0.9)])
                        trace_info['bandwidth_80pct_hz'] = f"{f_lo:.2f}–{f_hi:.2f}"
                except Exception:
                    pass
        except Exception:
            pass  # métricas opcionales

    # Analysis parameters
    formatted_params: dict = {}
    for key, value in analysis_params.items():
        if isinstance(value, float):
            formatted_params[key] = f"{value*100:.0f}%" if 'overlap' in key.lower() or key.endswith('_percent') else f"{value:.4g}"
        else:
            formatted_params[key] = _safe(value)

    return trace_info, formatted_params


def _render_ai_analysis_panel(trace, analysis_type: str, analysis_params: dict, container):
    """Render the AI analysis panel for spectrum analysis."""
    agents = _get_agent_suite()
    agent_error = st.session_state.get("ai_agents_error")
    
    if not agents:
        if agent_error:
            container.error(f"No se pudo inicializar el intérprete: {agent_error}")
        else:
            container.info("Configura los agentes IA en config/agents_config.yaml (asegura que exista 'spectrum_analyzer').")
        return
    
    if trace is None:
        container.info("Selecciona una traza para ejecutar el análisis IA.")
        return
    
    # Build context for AI analysis
    trace_info, formatted_params = _build_trace_context(trace, analysis_type, analysis_params)
    
    # Create unique keys for session state
    context_signature = f"{analysis_type}|{trace_info.get('station', 'UNK')}|{trace_info.get('channel', 'CH')}"
    context_key = "spectrum_ai_context"
    done_key = "spectrum_ai_auto_done"  
    result_key = "spectrum_ai_result"
    
    # Check if context changed
    if st.session_state.get(context_key) != context_signature:
        st.session_state[context_key] = context_signature
        st.session_state[done_key] = False
        st.session_state.pop(result_key, None)
    
    # Auto-run or manual trigger
    run_requested = False
    if not st.session_state.get(done_key, False):
        run_requested = True
    
    if container.button("Actualizar análisis IA", key="spectrum_ai_run"):
        run_requested = True
        st.session_state[done_key] = False
    
    if run_requested:
        with container.container():
            with st.spinner("Consultando intérprete espectral..."):
                try:
                    # Verificar que los datos estén completamente serializables antes de enviar
                    import json
                    json.dumps(trace_info)
                    json.dumps(formatted_params)
                    
                    analysis = run_spectrum_analysis(
                        agents,
                        trace_info=trace_info,
                        analysis_type=analysis_type,
                        analysis_params=formatted_params
                    )
                except (TypeError, ValueError) as json_err:
                    container.error(f"Error de serialización de datos: {json_err}")
                    analysis = None
                except Exception as exc:
                    handle_error(exc, context="Análisis IA Espectral")
                    analysis = None
            
            if analysis:
                st.session_state[result_key] = analysis
            else:
                container.warning("No se recibió respuesta del agente. Verifica que 'spectrum_analyzer' esté definido en agents_config.yaml.")
                st.session_state[result_key] = None
            st.session_state[done_key] = True
    
    # Display results
    current_analysis = st.session_state.get(result_key)
    if current_analysis:
        container.markdown(current_analysis)
    else:
        container.info("El intérprete IA aún no tiene resultados para este análisis.")


def main() -> None:
    st.header("🔍 Spectrum Analysis")
    st.caption("Análisis espectral independiente de trazas sísmicas.")
    
    # Mostrar ayuda contextual
    try:
        show_help("spectrum", expanded=False)
    except:
        pass  # Si no se puede mostrar ayuda, continuar sin ella
    
    session = get_session()

    # Verificar datos disponibles primero
    labels = list_trace_labels(session=session)
    if not labels:
        st.info("No hay trazas disponibles. Sube datos en el Uploader primero.")
        return

    # Controles compactos en fila horizontal
    st.markdown("**Selección de datos:**")
    dataset_names = list_dataset_names(session=session)
    current_dataset = get_current_stream_name(session=session)
    
    if dataset_names:
        ctrl_cols = st.columns([2, 3])
        with ctrl_cols[0]:
            selected_dataset = st.selectbox(
                "Dataset activo",
                options=dataset_names,
                index=dataset_names.index(current_dataset) if current_dataset in dataset_names else 0,
                key="spectrum_active_dataset",
            )
            if selected_dataset and selected_dataset != current_dataset:
                set_current_stream(selected_dataset, session=session)
                current_dataset = selected_dataset
                # Actualizar labels después del cambio de dataset
                labels = list_trace_labels(session=session)
        
        with ctrl_cols[1]:
            selected_label = st.selectbox(
                "Traza para análisis espectral",
                options=labels,
                index=0,
                help="Selecciona cualquier traza disponible para analizar su espectro"
            )
    else:
        selected_label = st.selectbox(
            "📊 Traza para análisis espectral",
            options=labels,
            index=0,
            help="Selecciona cualquier traza disponible para analizar su espectro"
        )
    
    if not selected_label:
        st.warning("Selecciona una traza para continuar.")
        return
        
    # Obtener la traza seleccionada
    trace = set_selected_trace(selected_label, session=session)
    if trace is None:
        st.error("No se pudo cargar la traza seleccionada.")
        return
    
    st.markdown("---")  # Separador visual
    
    # Tipo de análisis y configuración en una sola fila
    analysis_cols = st.columns([2, 2, 2, 2, 2])
    
    with analysis_cols[0]:
        analysis_type = st.selectbox(
            "🔬 Tipo de análisis",
            ["Espectrograma", "FFT", "Densidad Espectral (PSD)", "H/V Espectral (HVSR)"],
            index=0,
            help="HVSR requiere las tres componentes (E/N/Z o X/Y/Z) cargadas en el mismo dataset."
        )
    
    # Crear layout con columnas: gráfico (izquierda) + IA (derecha)
    col_plot, col_ai = st.columns([3, 2])
    
    # Variables para rastrear parámetros de análisis para IA
    analysis_params = {}
    
    with col_plot:
        # Controles específicos según tipo de análisis en la misma fila
        if analysis_type == "Espectrograma":
            with analysis_cols[1]:
                nfft = st.selectbox("NFFT", [128, 256, 512, 1024], index=1)
            with analysis_cols[2]:
                overlap = st.slider("Overlap %", 0, 90, 50, step=10) / 100.0
            with analysis_cols[3]:
                window = st.selectbox("Ventana", ["hanning", "hamming", "blackman"])
            with analysis_cols[4]:
                colorscale = st.selectbox("Escala color", ["Viridis", "Plasma", "Inferno", "Turbo"])
            
            analysis_params = {
                "nfft": nfft,
                "overlap_percent": overlap,
                "window": window,
                "colorscale": colorscale
            }
                
            # Generar espectrograma
            try:
                fig = create_spectrogram(trace, nfft=nfft, overlap=overlap, 
                                       window_type=window, colorscale=colorscale)
                st.plotly_chart(fig, use_container_width=True)
            except Exception as exc:
                st.error(f"Error al generar espectrograma: {exc}")
                
        elif analysis_type == "FFT":
            with analysis_cols[1]:
                log_scale = st.checkbox("Escala logarítmica", value=True)
            with analysis_cols[2]:
                freq_limit = st.slider("Límite freq (Hz)", 0, 50, 25)
            with analysis_cols[3]:
                window_fft = st.selectbox("Ventana FFT", ["hanning", "hamming", "blackman"], key="fft_window")
            with analysis_cols[4]:
                st.write("")  # Espaciador
            
            analysis_params = {
                "log_scale": log_scale,
                "freq_limit_hz": freq_limit,
                "window": window_fft
            }
                
            # Generar FFT
            try:
                fig = create_fft_plot(trace, log_scale=log_scale, freq_limit=freq_limit, 
                                    window_type=window_fft)
                st.plotly_chart(fig, use_container_width=True)
            except Exception as exc:
                st.error(f"Error al generar FFT: {exc}")
                
        elif analysis_type == "Densidad Espectral (PSD)":
            with analysis_cols[1]:
                nperseg = st.selectbox("Segmentos", [256, 512, 1024, 2048], index=1)
            with analysis_cols[2]:
                overlap_psd = st.slider("Overlap %", 0, 90, 75, step=5) / 100.0
            with analysis_cols[3]:
                freq_max = st.slider("Freq máx (Hz)", 1, 100, 50)
            with analysis_cols[4]:
                log_psd = st.checkbox("Escala log", value=True)
            
            analysis_params = {
                "nperseg": nperseg,
                "overlap_percent": overlap_psd,
                "freq_max_hz": freq_max,
                "log_scale": log_psd
            }
                
            # Generar PSD
            try:
                fig = create_psd_plot(trace, nperseg=nperseg, overlap=overlap_psd, 
                                    log_scale=log_psd, freq_max=freq_max)
                st.plotly_chart(fig, use_container_width=True)
            except Exception as exc:
                st.error(f"Error al generar PSD: {exc}")
        
        elif analysis_type == "H/V Espectral (HVSR)":
            with analysis_cols[1]:
                nperseg_hv = st.selectbox("Segmentos", [256, 512, 1024], index=1, key="hvsr_nperseg")
            with analysis_cols[2]:
                freq_min_hv = st.number_input("Freq min (Hz)", value=0.1, min_value=0.01, max_value=5.0, step=0.05, format="%.2f")
            with analysis_cols[3]:
                freq_max_hv = st.number_input("Freq max (Hz)", value=20.0, min_value=1.0, max_value=100.0, step=1.0)
            with analysis_cols[4]:
                smooth_oct = st.slider("Suavizado (octavas)", 0.0, 0.5, 0.1, step=0.05)

            analysis_params = {
                "nperseg": nperseg_hv,
                "freq_min_hz": freq_min_hv,
                "freq_max_hz": freq_max_hv,
                "smooth_octaves": smooth_oct,
            }

            # Detectar las tres componentes en el dataset actual
            all_labels = list_trace_labels(session=session)
            all_traces = get_traces_by_labels(all_labels, session=session)

            def _channel_axis(tr):
                ch = str(getattr(getattr(tr, "stats", None), "channel", "")).upper()
                if ch.endswith(("Z", "3")):
                    return "Z"
                if ch.endswith(("N", "Y", "2")):
                    return "H1"
                if ch.endswith(("E", "X", "1")):
                    return "H2"
                return None

            comp_map = {}
            for lbl, tr in zip(all_labels, all_traces):
                ax = _channel_axis(tr)
                if ax and ax not in comp_map:
                    comp_map[ax] = tr

            if all(k in comp_map for k in ("Z", "H1", "H2")):
                try:
                    fig = create_hvsr_plot(
                        comp_map["H1"], comp_map["H2"], comp_map["Z"],
                        nperseg=nperseg_hv,
                        freq_min=freq_min_hv,
                        freq_max=freq_max_hv,
                        smooth_octaves=smooth_oct,
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    st.caption(
                        "H/V calculado con método Nakamura (1989). "
                        "El pico f₀ indica la frecuencia de resonancia fundamental del suelo. "
                        "H1=canal N/Y/2 · H2=canal E/X/1 · Z=vertical."
                    )
                except Exception as exc:
                    st.error(f"Error al calcular HVSR: {exc}")
            else:
                found = list(comp_map.keys())
                missing = [k for k in ("Z", "H1", "H2") if k not in comp_map]
                st.warning(
                    f"HVSR requiere componentes Z, H1 (N/Y) y H2 (E/X). "
                    f"Encontradas: {found}. Faltan: {missing}. "
                    f"Carga un dataset con los tres canales."
                )

        # Información de la traza analizada
        if trace and hasattr(trace, 'stats'):
            st.markdown("---")
            info_cols = st.columns(4)
            stats = trace.stats
            with info_cols[0]:
                st.metric("Traza", selected_label)
            with info_cols[1]:
                st.metric("Fs (Hz)", f"{getattr(stats, 'sampling_rate', 'N/A')}")
            with info_cols[2]:
                st.metric("Muestras", f"{getattr(stats, 'npts', 'N/A')}")
            with info_cols[3]:
                duration = getattr(stats, 'npts', 0) / getattr(stats, 'sampling_rate', 1) if getattr(stats, 'sampling_rate', 0) > 0 else 0
                st.metric("Duración (s)", f"{duration:.1f}")

        # ── Espectro de respuesta vs. espectro de código ──────────────────
        st.markdown("---")
        with st.expander("📐 Espectro de Respuesta vs. Código Sísmico", expanded=False):
            import numpy as np
            import plotly.graph_objects as go

            st.caption(
                "Calcula el espectro de pseudoaceleración Sa(T, ξ=5%) del registro "
                "y lo superpone con el espectro de diseño del código seleccionado."
            )

            code_cols = st.columns([2, 2, 2])
            with code_cols[0]:
                code_choice = st.selectbox(
                    "Código de diseño",
                    ["NCh433 (Chile)", "ASCE 7-22 (USA)"],
                    key="spec_code_choice",
                )
            with code_cols[1]:
                damp_pct = st.slider("Amortiguamiento ξ (%)", 1, 20, 5, key="spec_damp")
                damping = damp_pct / 100.0
            with code_cols[2]:
                t_max_spec = st.slider("Período máximo (s)", 2.0, 10.0, 4.0, step=0.5, key="spec_tmax")

            # Parámetros específicos del código
            if code_choice == "NCh433 (Chile)":
                p_cols = st.columns(2)
                with p_cols[0]:
                    zone = st.selectbox(
                        "Zona sísmica",
                        options=[1, 2, 3],
                        index=2,  # default zona 3 (Antofagasta)
                        format_func=lambda z: NCH433_ZONES[z],
                        key="ncch433_zone",
                    )
                with p_cols[1]:
                    soil = st.selectbox(
                        "Tipo de suelo",
                        options=list(NCH433_SOILS.keys()),
                        index=1,  # default B
                        format_func=lambda s: NCH433_SOILS[s],
                        key="ncch433_soil",
                    )
            else:
                p_cols = st.columns(3)
                with p_cols[0]:
                    Ss = st.number_input("Ss [g]", value=1.0, min_value=0.05, max_value=3.0, step=0.05, key="asce7_ss")
                with p_cols[1]:
                    S1 = st.number_input("S1 [g]", value=0.4, min_value=0.02, max_value=1.5, step=0.02, key="asce7_s1")
                with p_cols[2]:
                    site_class = st.selectbox(
                        "Clase de sitio",
                        options=list(ASCE7_SITE_CLASSES.keys()),
                        index=2,
                        format_func=lambda s: ASCE7_SITE_CLASSES[s],
                        key="asce7_site",
                    )

            if st.button("Calcular espectro de respuesta", key="btn_calc_response_spec"):
                try:
                    # Calcular espectro de respuesta del registro
                    from scipy import signal as _scipy_signal
                    acc = np.asarray(trace.data, dtype=float)
                    dt = float(trace.stats.delta)
                    periods_rec = np.logspace(-2, np.log10(t_max_spec), 150)
                    sa_rec = np.zeros_like(periods_rec)

                    for j, T in enumerate(periods_rec):
                        if T < dt * 2:
                            sa_rec[j] = np.max(np.abs(acc))
                            continue
                        omega = 2.0 * np.pi / T
                        c = 2.0 * damping * omega
                        k = omega ** 2
                        b = [0, 0, k]
                        a_coef = [1, c, k]
                        try:
                            _, resp = _scipy_signal.lsim(
                                _scipy_signal.lti(b, a_coef), acc, np.arange(len(acc)) * dt
                            )
                            sa_rec[j] = float(np.max(np.abs(resp)))
                        except Exception:
                            sa_rec[j] = float(np.max(np.abs(acc)))

                    # Calcular espectro de código
                    if code_choice == "NCh433 (Chile)":
                        periods_code, sa_code = ncch433_spectrum(
                            zone=zone, soil=soil, damping=damping, t_max=t_max_spec
                        )
                        code_label = f"NCh433 Zona {zone}, Suelo {soil}"
                    else:
                        periods_code, sa_code = asce7_spectrum(
                            Ss=Ss, S1=S1, site_class=site_class, damping=damping, t_max=t_max_spec
                        )
                        code_label = f"ASCE 7-22 Clase {site_class}, Ss={Ss}g"

                    # Guardar en sesión para export + caché por dataset
                    _rspec_data = {
                        "periods_rec": periods_rec,
                        "sa_rec": sa_rec,
                        "periods_code": periods_code,
                        "sa_code": sa_code,
                        "code_label": code_label,
                    }
                    st.session_state["response_spec_data"] = _rspec_data
                    _ds_key = get_current_stream_name(session=session) or "unknown"
                    set_spectral_cache(_ds_key, "response_spec_data", _rspec_data, session=session)
                    mark_pipeline_step("V3_spectra", session=session)

                    # Gráfico
                    fig_rs = go.Figure()
                    fig_rs.add_trace(go.Scatter(
                        x=periods_rec, y=sa_rec,
                        mode="lines", name=f"Registro ({selected_label})",
                        line=dict(color="#74b9ff", width=2),
                    ))
                    fig_rs.add_trace(go.Scatter(
                        x=periods_code, y=sa_code,
                        mode="lines", name=code_label,
                        line=dict(color="#ff7675", width=2, dash="dash"),
                    ))
                    fig_rs.update_layout(
                        template="plotly_dark",
                        xaxis_title="Período T (s)",
                        yaxis_title="Sa (cm/s²)",
                        xaxis=dict(type="log", title="Período T (s)"),
                        hovermode="x unified",
                        height=400,
                        margin=dict(t=30, b=40),
                        legend=dict(x=0.01, y=0.99),
                    )
                    st.plotly_chart(fig_rs, use_container_width=True)

                    # Resumen de exceedance
                    try:
                        sa_rec_at_code = np.interp(periods_code, periods_rec, sa_rec)
                        ratio = sa_rec_at_code / np.where(sa_code > 0, sa_code, 1e-9)
                        pct_exceed = float(np.mean(ratio > 1.0) * 100)
                        max_ratio = float(np.max(ratio))
                        st.info(
                            f"El registro **supera** el espectro de diseño en "
                            f"**{pct_exceed:.0f}%** de los períodos analizados. "
                            f"Ratio máximo: **{max_ratio:.2f}×**"
                        )
                    except Exception:
                        pass

                except Exception as exc:
                    st.error(f"Error al calcular espectro de respuesta: {exc}")

            # Exportación CSV del espectro si existe
            _ds_key_r = get_current_stream_name(session=session) or "unknown"
            rs_data = (get_spectral_cache(_ds_key_r, "response_spec_data", session=session)
                       or st.session_state.get("response_spec_data"))
            if rs_data:
                import pandas as pd, io
                df_rs = pd.DataFrame({
                    "T_s": rs_data["periods_rec"],
                    f"Sa_registro_cms2": rs_data["sa_rec"],
                })
                df_code = pd.DataFrame({
                    "T_s": rs_data["periods_code"],
                    f"Sa_{rs_data['code_label'].replace(' ', '_')}_cms2": rs_data["sa_code"],
                })
                csv_buf = io.StringIO()
                df_rs.to_csv(csv_buf, index=False)
                st.download_button(
                    "⬇️ Exportar espectros CSV",
                    data=csv_buf.getvalue(),
                    file_name="espectros_respuesta.csv",
                    mime="text/csv",
                    key="dl_spec_csv",
                )

        # ── Exportación PEER AT2 ───────────────────────────────────────────
        with st.expander("📤 Exportar acelerograma — Formato PEER AT2", expanded=False):
            st.caption(
                "Formato PEER AT2: compatible con SeismoSignal, SeismoMatch y PEER NGA. "
                "Requiere que los datos estén en cm/s²."
            )
            at2_label = st.text_input(
                "Descripción del registro",
                value=f"{selected_label} — {session.dataset_name or 'dataset'}",
                key="at2_label",
            )
            at2_units = st.selectbox(
                "Unidades de los datos",
                ["cm/s²", "g", "m/s²", "counts"],
                key="at2_units",
            )
            if st.button("Generar archivo AT2", key="btn_gen_at2"):
                try:
                    import numpy as np
                    acc = np.asarray(trace.data, dtype=float)
                    dt = float(trace.stats.delta)
                    npts = len(acc)

                    # Encabezado PEER AT2
                    header = (
                        f"PEER AT2 — {at2_label}\n"
                        f"Record generated by SeismicAI — {session.dataset_name or 'dataset'}\n"
                        f"NPTS={npts}, DT={dt:.6f} SEC, {at2_units}\n"
                        f"NPTS={npts}, DT={dt:.6f}\n"
                    )
                    # Datos: 8 valores por línea (estándar PEER)
                    data_lines = []
                    for i in range(0, npts, 8):
                        chunk = acc[i:i + 8]
                        data_lines.append("  ".join(f"{v:12.6E}" for v in chunk))
                    at2_content = header + "\n".join(data_lines)

                    st.download_button(
                        "⬇️ Descargar AT2",
                        data=at2_content,
                        file_name=f"{selected_label.replace('.', '_')}.AT2",
                        mime="text/plain",
                        key="dl_at2_file",
                    )
                    st.success("Archivo AT2 listo.")
                except Exception as exc:
                    st.error(f"Error al generar AT2: {exc}")

        # ── RotD50 / RotD100 ──────────────────────────────────────────────
        st.markdown("---")
        with st.expander("🔄 Espectro RotD50 / RotD100 (PEER)", expanded=False):
            import numpy as np
            import plotly.graph_objects as go

            st.caption(
                "Rota las dos componentes horizontales de 0° a 180° y calcula "
                "la mediana (RotD50) y el máximo (RotD100) del espectro de respuesta. "
                "Requiere dos componentes horizontales en el dataset activo."
            )

            # Identificar componentes horizontales disponibles
            stream_rd = get_current_stream(session)
            h_traces = []
            if stream_rd:
                for tr in stream_rd:
                    ch = getattr(getattr(tr, "stats", None), "channel", "")
                    if ch and ch[-1].upper() in ("E", "N", "1", "2", "X", "Y"):
                        h_traces.append(tr)

            if len(h_traces) < 2:
                st.warning(
                    "Se necesitan al menos 2 componentes horizontales (canales E/N, 1/2 o X/Y). "
                    f"Encontradas: {[str(t.id) for t in h_traces]}."
                )
            else:
                # Selectores
                h_labels = [str(t.id) for t in h_traces]
                rd_cols = st.columns([2, 2, 2, 1])
                with rd_cols[0]:
                    rd_comp1 = st.selectbox("Componente 1", h_labels, key="rd_comp1")
                with rd_cols[1]:
                    rd_comp2 = st.selectbox(
                        "Componente 2",
                        [l for l in h_labels if l != rd_comp1] or h_labels,
                        key="rd_comp2",
                    )
                with rd_cols[2]:
                    rd_damp_pct = st.slider("Amortiguamiento ξ (%)", 1, 20, 5, key="rd_damp")
                with rd_cols[3]:
                    rd_tmax = st.number_input("T_max (s)", 0.5, 10.0, 4.0, step=0.5, key="rd_tmax")

                if st.button("Calcular RotD50 / RotD100", key="btn_rotd"):
                    tr1 = next((t for t in h_traces if str(t.id) == rd_comp1), None)
                    tr2 = next((t for t in h_traces if str(t.id) == rd_comp2), None)
                    if tr1 is None or tr2 is None:
                        st.error("No se encontraron las componentes seleccionadas.")
                    else:
                        try:
                            with st.spinner("Calculando RotD50…"):
                                dt1 = float(tr1.stats.delta)
                                dt2 = float(tr2.stats.delta)
                                dt_rd = min(dt1, dt2)
                                res = compute_rotd(
                                    np.asarray(tr1.data, dtype=float),
                                    np.asarray(tr2.data, dtype=float),
                                    dt=dt_rd,
                                    damping=rd_damp_pct / 100.0,
                                    t_max=rd_tmax,
                                    comp1_id=rd_comp1,
                                    comp2_id=rd_comp2,
                                )

                            st.session_state["rotd_result"] = res
                            _ds_key = get_current_stream_name(session=session) or "unknown"
                            set_spectral_cache(_ds_key, "rotd_result", res, session=session)
                            mark_pipeline_step("V3_spectra", session=session)

                            fig_rd = go.Figure()
                            fig_rd.add_trace(go.Scatter(
                                x=res.periods, y=res.rotd50,
                                mode="lines", name="RotD50",
                                line=dict(color="#74b9ff", width=2),
                            ))
                            fig_rd.add_trace(go.Scatter(
                                x=res.periods, y=res.rotd100,
                                mode="lines", name="RotD100",
                                line=dict(color="#fd79a8", width=1.5, dash="dot"),
                            ))
                            fig_rd.update_layout(
                                template="plotly_dark",
                                xaxis=dict(type="log", title="Período T (s)"),
                                yaxis_title="Sa (cm/s²)",
                                title=f"RotD50/RotD100 — ξ={rd_damp_pct}%",
                                height=380,
                                margin=dict(t=40, b=40),
                                hovermode="x unified",
                                legend=dict(x=0.01, y=0.99),
                            )
                            st.plotly_chart(fig_rd, use_container_width=True)

                            # Ratio RotD100/RotD50
                            ratio_rd = np.where(res.rotd50 > 0, res.rotd100 / res.rotd50, 1.0)
                            st.info(
                                f"Ratio RotD100/RotD50 — Mediana: {float(np.median(ratio_rd)):.2f} × "
                                f"| Máximo: {float(np.max(ratio_rd)):.2f} ×"
                            )

                        except Exception as exc:
                            st.error(f"Error en RotD50: {exc}")

                # Exportación CSV si existe resultado
                _ds_key_rd = get_current_stream_name(session=session) or "unknown"
                rd_res = (get_spectral_cache(_ds_key_rd, "rotd_result", session=session)
                          or st.session_state.get("rotd_result"))
                if rd_res is not None:
                    import pandas as pd, io as _io2
                    df_rd = pd.DataFrame({
                        "T_s": rd_res.periods,
                        "RotD50_cms2": rd_res.rotd50,
                        "RotD100_cms2": rd_res.rotd100,
                    })
                    csv_rd = _io2.StringIO()
                    df_rd.to_csv(csv_rd, index=False)
                    st.download_button(
                        "⬇️ Exportar RotD50/RotD100 CSV",
                        data=csv_rd.getvalue(),
                        file_name=f"rotd_{rd_res.comp1_id}_{rd_res.comp2_id}.csv",
                        mime="text/csv",
                        key="dl_rotd_csv",
                    )

        # ── HVSR (Nakamura / SESAME) ──────────────────────────────────────
        st.markdown("---")
        with st.expander("🌊 HVSR — Caracterización de Sitio (SESAME)", expanded=False):
            import numpy as np
            import plotly.graph_objects as go

            st.caption(
                "Relación espectral H/V por el método Nakamura (1989) con suavizado "
                "Konno-Ohmachi y criterios de validación SESAME. "
                "Requiere 3 componentes: Z (vertical) y dos horizontales."
            )

            stream_hv = get_current_stream(session)
            z_traces, h_traces_hv = [], []
            if stream_hv:
                for tr in stream_hv:
                    ch = getattr(getattr(tr, "stats", None), "channel", "")
                    if not ch:
                        continue
                    last = ch[-1].upper()
                    if last == "Z":
                        z_traces.append(tr)
                    elif last in ("E", "N", "1", "2", "X", "Y"):
                        h_traces_hv.append(tr)

            if len(z_traces) < 1 or len(h_traces_hv) < 2:
                st.warning(
                    "HVSR requiere 1 componente vertical (Z) y 2 horizontales (E/N o 1/2). "
                    f"Verticales: {[t.id for t in z_traces]} | "
                    f"Horizontales: {[t.id for t in h_traces_hv]}"
                )
            else:
                hv_cols = st.columns(3)
                z_labels  = [str(t.id) for t in z_traces]
                h1_labels = [str(t.id) for t in h_traces_hv]

                with hv_cols[0]:
                    hv_z_sel  = st.selectbox("Componente Z (vertical)", z_labels, key="hv_z")
                    hv_h1_sel = st.selectbox("Componente H1", h1_labels, key="hv_h1")
                    hv_h2_sel = st.selectbox(
                        "Componente H2",
                        [l for l in h1_labels if l != hv_h1_sel] or h1_labels,
                        key="hv_h2",
                    )
                with hv_cols[1]:
                    hv_win = st.slider("Ventana (s)", 5, 60, 20, step=5, key="hv_win")
                    hv_ko_b = st.slider("Konno-Ohmachi b", 10, 80, 40, step=5, key="hv_ko_b")
                with hv_cols[2]:
                    hv_fmin = st.number_input("f_min (Hz)", 0.01, 5.0, 0.1, step=0.05, key="hv_fmin")
                    hv_fmax = st.number_input("f_max (Hz)", 1.0, 50.0, 20.0, step=1.0, key="hv_fmax")

                if st.button("Calcular HVSR", key="btn_hvsr"):
                    tr_z  = next((t for t in z_traces  if str(t.id) == hv_z_sel), None)
                    tr_h1 = next((t for t in h_traces_hv if str(t.id) == hv_h1_sel), None)
                    tr_h2 = next((t for t in h_traces_hv if str(t.id) == hv_h2_sel), None)

                    if not (tr_z and tr_h1 and tr_h2):
                        st.error("No se encontraron las trazas seleccionadas.")
                    else:
                        try:
                            with st.spinner("Calculando HVSR…"):
                                dt_hv = float(tr_z.stats.delta)
                                hv_res = compute_hvsr(
                                    acc_h1=np.asarray(tr_h1.data, dtype=float),
                                    acc_h2=np.asarray(tr_h2.data, dtype=float),
                                    acc_z=np.asarray(tr_z.data, dtype=float),
                                    dt=dt_hv,
                                    window_len_s=float(hv_win),
                                    ko_b=float(hv_ko_b),
                                    freq_min=float(hv_fmin),
                                    freq_max=float(hv_fmax),
                                )

                            st.session_state["hvsr_result"] = hv_res
                            _ds_key = get_current_stream_name(session=session) or "unknown"
                            set_spectral_cache(_ds_key, "hvsr_result", hv_res, session=session)

                            # Gráfico H/V con banda ±1σ
                            fig_hv = go.Figure()
                            fig_hv.add_trace(go.Scatter(
                                x=hv_res.freqs, y=hv_res.hv_plus1,
                                mode="lines", line=dict(width=0),
                                showlegend=False, name="+1σ",
                            ))
                            fig_hv.add_trace(go.Scatter(
                                x=hv_res.freqs, y=hv_res.hv_minus1,
                                mode="lines", line=dict(width=0),
                                fill="tonexty",
                                fillcolor="rgba(116,185,255,0.18)",
                                name="±1σ",
                            ))
                            fig_hv.add_trace(go.Scatter(
                                x=hv_res.freqs, y=hv_res.hv_mean,
                                mode="lines", name="H/V media",
                                line=dict(color="#74b9ff", width=2.5),
                            ))
                            # Línea de pico f0
                            fig_hv.add_vline(
                                x=hv_res.f0_hz,
                                line=dict(color="#fdcb6e", dash="dash", width=1.5),
                                annotation_text=f"f₀={hv_res.f0_hz:.2f} Hz",
                                annotation_position="top right",
                            )
                            # Línea umbral SESAME A(f0)≥2
                            fig_hv.add_hline(
                                y=2.0,
                                line=dict(color="orange", dash="dot", width=1),
                                annotation_text="SESAME A≥2",
                            )
                            fig_hv.update_layout(
                                template="plotly_dark",
                                xaxis=dict(type="log", title="Frecuencia (Hz)"),
                                yaxis_title="H/V",
                                title=f"HVSR — f₀={hv_res.f0_hz:.2f} Hz · T₀={hv_res.t0_s:.2f} s · {hv_res.n_windows} ventanas",
                                height=380,
                                margin=dict(t=50, b=40),
                                hovermode="x unified",
                            )
                            st.plotly_chart(fig_hv, use_container_width=True)

                            # Métricas clave
                            m1, m2, m3, m4 = st.columns(4)
                            m1.metric("f₀ (Hz)",   f"{hv_res.f0_hz:.3f}")
                            m2.metric("T₀ (s)",    f"{hv_res.t0_s:.3f}")
                            m3.metric("A(f₀)",     f"{hv_res.a0:.2f}")
                            m4.metric("Ventanas",  str(hv_res.n_windows))

                            # Criterios SESAME
                            with st.expander("Criterios de validación SESAME", expanded=True):
                                st.code(hv_res.sesame.summary, language=None)

                        except Exception as exc:
                            st.error(f"Error en HVSR: {exc}")

                # Exportación CSV si existe resultado
                _ds_key_hv = get_current_stream_name(session=session) or "unknown"
                hv_data = (get_spectral_cache(_ds_key_hv, "hvsr_result", session=session)
                           or st.session_state.get("hvsr_result"))
                if hv_data is not None:
                    import pandas as pd, io as _io3
                    df_hv = pd.DataFrame({
                        "freq_hz":   hv_data.freqs,
                        "hv_mean":   hv_data.hv_mean,
                        "hv_std":    hv_data.hv_std,
                        "hv_plus1":  hv_data.hv_plus1,
                        "hv_minus1": hv_data.hv_minus1,
                    })
                    csv_hv = _io3.StringIO()
                    df_hv.to_csv(csv_hv, index=False)
                    st.download_button(
                        "⬇️ Exportar HVSR CSV",
                        data=csv_hv.getvalue(),
                        file_name="hvsr_result.csv",
                        mime="text/csv",
                        key="dl_hvsr_csv",
                    )

    # Panel de análisis IA en la columna derecha
    with col_ai:
        st.subheader("Intérprete IA Espectral")
        _render_ai_analysis_panel(trace, analysis_type, analysis_params, col_ai)


if __name__ == "__main__":  # pragma: no cover
    main()
