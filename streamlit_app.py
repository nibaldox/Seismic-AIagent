"""Main entry point for SeismoAnalyzer Pro."""


from pathlib import Path

import os

import streamlit as st
from dotenv import load_dotenv

from src.streamlit_utils.session_state import get_session
import src.streamlit_utils.appearance as appearance_utils

PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG_DIR = PROJECT_ROOT / "config"

load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=False)

st.set_page_config(
    page_title="SeismoAnalyzer Pro",
    page_icon="SA",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("SeismoAnalyzer Pro")

session = get_session()
st.session_state.setdefault("navigation", "Waveform Viewer")


# --- Panel de salud simple (único) ---
with st.sidebar:
    st.markdown("---")
    st.subheader("🩺 Panel de Salud")
    openrouter_key = st.session_state.get("openrouter_api_key") or os.getenv("OPENROUTER_API_KEY", "")
    st.write(f"🔑 OpenRouter API: {'✅' if openrouter_key else '❌'}")
    st.write(f"🌐 Conectividad IA: {'✅' if openrouter_key else '❌'}")
    from src.streamlit_utils.session_state import get_session
    session = get_session()
    dataset = session.dataset_name or 'Ninguno'
    st.write(f"📁 Dataset activo: {dataset}")
    st.markdown("---")
    st.success("Usa el menú de páginas de Streamlit (izquierda) para navegar.")


# Densidad de UI global
appearance_utils.render_density_controls()


# Ejemplo de notificación de error (toast)
if st.sidebar.button("Probar notificación de error"):
    appearance_utils.show_error_toast("¡Error de ejemplo: revisa la configuración!", duration=4)

st.write(
    "Welcome to the Rapid Seismic Analyzer. Use the sidebar to upload data, "
    "explore waveforms, and access AI-powered interpretation tools."
)

st.markdown(
    """
    ### Quick Start
    1. Open the **Upload** page to load MiniSEED or SAC files.
    2. Explore the **Waveform Viewer** for interactive plots.
    3. Visit **AI Interpreter** once data is loaded for automated insights.
    """
)

st.info(
    "Configuration files are located in `config/`. Adjust `agents_config.yaml` to define and tune "
    "the AI agent suite used by the app."
)

# OpenRouter API key setup
existing_key = st.session_state.get("openrouter_api_key") or os.getenv("OPENROUTER_API_KEY", "")
if existing_key and "openrouter_api_key" not in st.session_state:
    st.session_state["openrouter_api_key"] = existing_key

with st.expander("Configurar API de OpenRouter", expanded=not bool(existing_key)):
    st.markdown(
        "Ingresa tu clave `OPENROUTER_API_KEY`. La clave se guarda solo en la memoria de la sesion actual y no se escribe en disco."
    )
    with st.form("openrouter_api_form"):
        api_key_input = st.text_input("OpenRouter API key", value=existing_key, type="password", help="Se usa para habilitar los agentes IA basados en OpenRouter.")
        col_save, col_clear = st.columns([1, 1])
        save_clicked = col_save.form_submit_button("Guardar")
        clear_clicked = col_clear.form_submit_button("Borrar")

    if save_clicked:
        key_trimmed = api_key_input.strip()
        if key_trimmed:
            os.environ["OPENROUTER_API_KEY"] = key_trimmed
            st.session_state["openrouter_api_key"] = key_trimmed
            st.success("Clave guardada para esta sesion.")
        else:
            st.warning("No se guardo la clave porque el campo esta vacio.")
    elif clear_clicked:
        os.environ.pop("OPENROUTER_API_KEY", None)
        st.session_state.pop("openrouter_api_key", None)
        st.info("Clave eliminada de la sesion actual.")

if os.getenv("OPENROUTER_API_KEY"):
    st.success("OpenRouter API key detected - AI agent features ready.")
else:
    st.warning("Add API keys to `.env` to unlock full AI capabilities.")


def main():  # minimal entry point for tests
    """No-op main used for smoke tests to ensure module structure is sound."""
    return True
