"""Punto de entrada principal — SeismoAnalyzer Pro."""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from src.streamlit_utils.session_state import (
    get_session,
    get_current_stream_name,
    list_dataset_names,
    set_current_stream,
    get_pipeline_steps,
)
import src.streamlit_utils.appearance as appearance_utils

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=False)

st.set_page_config(
    page_title="SeismoAnalyzer Pro",
    page_icon="🌋",
    layout="wide",
    initial_sidebar_state="expanded",
)

session = get_session()

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR GLOBAL
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/?size=48&id=E8HxdZU7LHXG&format=png", width=48)
    st.markdown("## SeismoAnalyzer Pro")
    st.divider()

    # ── Dataset activo ────────────────────────────────────────────────────
    st.subheader("📁 Dataset activo")
    dataset_names = list_dataset_names(session=session)
    current_dataset = get_current_stream_name(session=session)

    if dataset_names:
        selected_ds = st.selectbox(
            "Seleccionar dataset",
            options=dataset_names,
            index=dataset_names.index(current_dataset) if current_dataset in dataset_names else 0,
            key="sidebar_global_dataset",
            label_visibility="collapsed",
        )
        if selected_ds and selected_ds != current_dataset:
            set_current_stream(selected_ds, session=session)
            st.rerun()
        st.caption(f"**{current_dataset or 'Ninguno'}**")
    else:
        st.info("Sin datasets. Carga datos desde **Uploader** o **Batch Loader**.")

    # ── Indicador pipeline V0 → V3 ────────────────────────────────────────
    st.subheader("⚙️ Estado del pipeline")

    _PIPELINE_STAGES = [
        ("V0", "Datos cargados",      "V0_loaded"),
        ("V1", "Filtrado/Baseline",   "V1_filtered"),
        ("V2", "IMs calculados",      "V2_ims"),
        ("V3", "Espectros / código",  "V3_spectra"),
    ]
    steps_done = set(get_pipeline_steps(session=session))
    # Auto-detectar V0 si hay dataset activo
    if current_dataset:
        steps_done.add("V0_loaded")

    for label, desc, key in _PIPELINE_STAGES:
        done = key in steps_done
        icon = "✅" if done else "⬜"
        color = "#55efc4" if done else "#636e72"
        st.markdown(
            f"<span style='color:{color};font-weight:bold'>{icon} {label}</span>"
            f" <span style='color:#b2bec3;font-size:0.85em'>{desc}</span>",
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Picks P/S ─────────────────────────────────────────────────────────
    from src.streamlit_utils.session_state import list_picks
    picks_count = len(list_picks(session=session))
    if picks_count > 0:
        st.caption(f"🔵 {picks_count} pick(s) P/S en sesión")

    # ── Estado del modelo IA ──────────────────────────────────────────────
    st.subheader("🤖 Modelo IA activo")
    active_model = st.session_state.get("selected_ai_model", "nvidia/nemotron-3-super-120b-a12b:free")
    if active_model.startswith("lmstudio:"):
        lm_url = st.session_state.get("lmstudio_base_url", "http://127.0.0.1:1234/v1")
        try:
            import httpx
            r = httpx.get(lm_url.replace("/v1", "/v1/models"), timeout=2.0)
            lm_ok = r.status_code == 200
        except Exception:
            lm_ok = False
        st.write(f"🖥️ LM Studio: {'✅' if lm_ok else '❌'}")
        st.caption(active_model[len("lmstudio:"):])
    else:
        openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
        st.write(f"🌐 OpenRouter: {'✅' if openrouter_key else '❌ Sin API key'}")
        short = active_model.split("/")[-1][:30]
        st.caption(short)

# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────
st.title("🌋 SeismoAnalyzer Pro")
st.caption("Plataforma de análisis sísmico para acelerógrafos Kelunji/ACE con IA interpretativa.")

# ── Quick Start ───────────────────────────────────────────────────────────────
# st.columns() solo funciona con el runtime activo de Streamlit.
# Durante la importación del módulo (ej. en tests) puede devolver ();
# verificamos la longitud antes de unpacking para evitar ValueError.
_qs_cols = st.columns(5)
if len(_qs_cols) == 5:
    col_qs1, col_qs2, col_qs3, col_qs4, col_qs5 = _qs_cols
    col_qs1.info("**1. Carga datos**\nUsa **Uploader** (archivos individuales) o **Batch Loader** (carpeta completa)")
    col_qs2.info("**2. Visualiza**\nExplora waveforms, aplica filtros y corrección de baseline en **Waveform Viewer**")
    col_qs3.info("**3. Analiza**\nCalcula IMs, espectros, HVSR y RotD50 en **Spectrum Analysis**")
    col_qs4.info("**4. Interpreta**\nEjecuta el equipo IA multi-agente en **AI Interpreter**")
    col_qs5.info("**5. Exporta**\nGenera el informe final integrado en **Reporte Final** (HTML + Excel)")
    st.divider()
# si len != 5: streamlit runtime no disponible (ej. durante importación en tests) — se omite el Quick Start

# ── Configuración modelo IA ────────────────────────────────────────────────
with st.expander("🤖 Configuración de Modelo IA", expanded=not bool(os.getenv("OPENROUTER_API_KEY"))):
    model_options = {
        "nvidia/nemotron-3-super-120b-a12b:free": "NVIDIA Nemotron Super 120B",
        "moonshotai/kimi-k2:free":                "Moonshot Kimi K2",
        "x-ai/grok-4-fast:free":                  "xAI Grok 4 Fast",
        "z-ai/glm-4.5-air:free":                  "Z-AI GLM 4.5 Air",
        "qwen/qwen3-235b-a22b:free":              "Qwen3 235B",
        "meituan/longcat-flash-chat":             "Meituan LongCat Flash",
        "__lmstudio__":                            "🖥️ LM Studio (local)",
    }

    current_model = st.session_state.get("selected_ai_model", "nvidia/nemotron-3-super-120b-a12b:free")
    selectbox_value = (
        "__lmstudio__" if current_model.startswith("lmstudio:")
        else (current_model if current_model in model_options else "nvidia/nemotron-3-super-120b-a12b:free")
    )

    selected_option = st.selectbox(
        "Modelo para análisis IA:",
        options=list(model_options.keys()),
        index=list(model_options.keys()).index(selectbox_value),
        format_func=lambda x: model_options[x],
        key="home_model_selector",
    )

    if selected_option == "__lmstudio__":
        st.info("**LM Link (Tailscale):** el túnel hace que el modelo remoto aparezca como localhost.")
        col_lm1, col_lm2 = st.columns([2, 1])
        with col_lm1:
            lm_model_name = st.text_input(
                "Nombre del modelo en LM Studio",
                value=st.session_state.get("lmstudio_model_name", "llama-3.2-3b-instruct"),
            )
        with col_lm2:
            lm_base_url = st.text_input(
                "URL del servidor",
                value=st.session_state.get("lmstudio_base_url", "http://127.0.0.1:1234/v1"),
                placeholder="http://127.0.0.1:1234/v1",
            )
        selected_model = f"lmstudio:{lm_model_name.strip()}"
        st.session_state["lmstudio_model_name"] = lm_model_name.strip()
        st.session_state["lmstudio_base_url"] = lm_base_url.strip()
        os.environ["LMSTUDIO_BASE_URL"] = lm_base_url.strip()
    else:
        selected_model = selected_option

    if selected_model != current_model:
        st.session_state["selected_ai_model"] = selected_model
        for k in [k for k in st.session_state if isinstance(k, str) and k.startswith("ai_agents_")]:
            del st.session_state[k]
        st.success(f"Modelo actualizado: {model_options.get(selected_option, selected_model)}")
        st.rerun()

    # API key OpenRouter
    st.markdown("---")
    existing_key = st.session_state.get("openrouter_api_key") or os.getenv("OPENROUTER_API_KEY", "")
    if existing_key and "openrouter_api_key" not in st.session_state:
        st.session_state["openrouter_api_key"] = existing_key

    with st.form("openrouter_api_form"):
        api_key_input = st.text_input(
            "OpenRouter API key",
            value=existing_key,
            type="password",
        )
        col_save, col_clear = st.columns(2)
        save_clicked = col_save.form_submit_button("Guardar clave")
        clear_clicked = col_clear.form_submit_button("Borrar clave")

    if save_clicked and api_key_input.strip():
        os.environ["OPENROUTER_API_KEY"] = api_key_input.strip()
        st.session_state["openrouter_api_key"] = api_key_input.strip()
        st.success("Clave guardada para esta sesión.")
    elif clear_clicked:
        os.environ.pop("OPENROUTER_API_KEY", None)
        st.session_state.pop("openrouter_api_key", None)
        st.info("Clave eliminada.")

st.divider()

# ── Resumen de datasets cargados ──────────────────────────────────────────
st.subheader("📊 Datasets en sesión")
if dataset_names:
    for ds in dataset_names:
        badge = "🟢" if ds == current_dataset else "⚪"
        st.markdown(f"{badge} `{ds}`")
else:
    st.info("No hay datasets cargados. Ve a **Uploader** (página 00) o **Batch Loader** (página 01).")

appearance_utils.render_density_controls()


def main():
    return True
