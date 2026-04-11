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
    get_current_stream_name,
    get_selected_trace,
    get_selected_trace_label,
    get_session,
    list_dataset_names,
    list_trace_labels,
    set_current_stream,
    set_selected_trace,
    get_traces_by_labels,
)
from src.streamlit_utils.appearance import handle_error
from src.visualization.spectrum_plots import create_spectrogram, create_fft_plot, create_psd_plot
from src.ai_agent.seismic_interpreter import load_agent_suite, run_spectrum_analysis

st.set_page_config(page_title="Spectrum Analysis", page_icon="🔍")


def _get_agent_suite():
    """Get AI agents for spectrum analysis with dynamic model selection."""
    # Obtener modelo seleccionado desde session_state
    selected_model = st.session_state.get("selected_ai_model", "deepseek/deepseek-chat-v3.1:free")
    
    # Usar clave de caché basada en el modelo para evitar recreación innecesaria
    cache_key = f"ai_agents_{selected_model.replace('/', '_').replace(':', '_')}"
    
    if cache_key not in st.session_state:
        try:
            # Crear configuración dinámica para el modelo seleccionado si existe
            try:
                from src.ai_agent.dynamic_config import get_dynamic_config_path
                dynamic_config_path = get_dynamic_config_path(selected_model)
                agents = load_agent_suite(dynamic_config_path)
            except ImportError:
                # Fallback a configuración estática si dynamic_config no está disponible
                agents = load_agent_suite()
            
            st.session_state[cache_key] = agents
            st.session_state.pop("ai_agents_error", None)
            
            # Limpiar cachés de otros modelos para liberar memoria
            keys_to_remove = [k for k in st.session_state.keys() if isinstance(k, str) and k.startswith("ai_agents_") and k != cache_key]
            for k in keys_to_remove:
                del st.session_state[k]
                
        except Exception as exc:
            st.session_state["ai_agents_error"] = str(exc)
            st.session_state[cache_key] = {}
    
    return st.session_state.get(cache_key, {})


def _build_trace_context(trace, analysis_type: str, analysis_params: dict) -> tuple[dict, dict]:
    """Build context for AI analysis of spectral data."""
    
    # Helper para conversión segura a JSON
    def to_json_safe(value):
        if value is None:
            return None
        # Manejar UTCDateTime de ObsPy
        if hasattr(value, 'isoformat'):
            return value.isoformat()
        elif hasattr(value, '__str__'):
            return str(value)
        return value
    
    # Trace information
    trace_info = {}
    if hasattr(trace, 'stats'):
        stats = trace.stats
        trace_info['station'] = to_json_safe(getattr(stats, 'station', 'Unknown'))
        trace_info['channel'] = to_json_safe(getattr(stats, 'channel', 'Unknown'))  
        trace_info['sampling_rate'] = f"{getattr(stats, 'sampling_rate', 0)} Hz"
        trace_info['npts'] = getattr(stats, 'npts', 0)
        
        # Conversión segura de timestamps
        if hasattr(stats, 'starttime'):
            trace_info['start_time'] = to_json_safe(stats.starttime)
        if hasattr(stats, 'endtime'):
            trace_info['end_time'] = to_json_safe(stats.endtime)
            
        if hasattr(stats, 'delta') and hasattr(stats, 'npts'):
            duration = stats.delta * stats.npts
            trace_info['duration'] = f"{duration:.2f} seconds"
    
    # Analysis parameters formatted for AI
    formatted_params = {}
    for key, value in analysis_params.items():
        if isinstance(value, float):
            if key.endswith('_percent') or 'overlap' in key.lower():
                formatted_params[key] = f"{value*100:.0f}%"
            else:
                formatted_params[key] = f"{value:.3f}"
        else:
            formatted_params[key] = to_json_safe(value)
    
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
                    analysis = run_spectrum_analysis(
                        agents,
                        trace_info=trace_info,
                        analysis_type=analysis_type,
                        analysis_params=formatted_params
                    )
                except Exception as exc:
                    handle_error(exc, context="Análisis IA Espectral")
                    analysis = None
            
            if analysis:
                st.session_state[result_key] = analysis
            else:
                container.warning("No se recibió respuesta del agente. Verifica que 'spectrum_analysis' esté definido en agents_config.yaml.")
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
            ["Espectrograma", "FFT", "Densidad Espectral (PSD)"],
            index=0
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
    
    # Panel de análisis IA en la columna derecha
    with col_ai:
        st.subheader("Intérprete IA Espectral")
        _render_ai_analysis_panel(trace, analysis_type, analysis_params, col_ai)


if __name__ == "__main__":  # pragma: no cover
    main()
