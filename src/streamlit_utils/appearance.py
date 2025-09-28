
from __future__ import annotations
# --- Manejador de errores unificado ---
def handle_error(exc: Exception, *, context: str = "") -> None:
    """Muestra error con contexto y tipo en formato consistente."""
    msg = f"{context}: {type(exc).__name__}: {exc}" if context else f"{type(exc).__name__}: {exc}"
    show_error_toast(msg, duration=5)
"""Utilidades de apariencia/UX compartidas (densidad, estilos)."""

import streamlit as st



def _inject_max_width_css(max_width: int = 1800) -> None:
    """Ajusta el ancho maximo del contenedor principal."""
    st.markdown(
        f"""
        <style>
        .block-container {{
            max-width: {max_width}px;
        }}
        </style>
        """
    , unsafe_allow_html=True)


def _inject_compact_css() -> None:
    """Inyecta estilos compactos para reducir padding/margenes generales."""
    st.markdown(
        """
        <style>
        /* Reducir padding general del contenedor principal */
        .block-container { padding-top: 0.6rem; padding-bottom: 0.8rem; }

        /* Sidebar mas compacto */
        [data-testid="stSidebar"] .block-container { padding-top: 0.6rem; padding-bottom: 0.8rem; }

        /* Botones y controles mas densos */
        .stButton>button { padding: 0.25rem 0.6rem; line-height: 1.1; }
        .stDownloadButton>button { padding: 0.25rem 0.6rem; line-height: 1.1; }

        /* Inputs */
        .stTextInput input, .stNumberInput input, .stTextArea textarea { padding-top: 0.25rem; padding-bottom: 0.25rem; }
        .stSelectbox [data-baseweb="select"]>div { min-height: 32px; }

        /* Expander encabezado y cuerpo */
        details>summary { padding: 0.35rem 0.5rem; }
        .stExpander>div>div { padding: 0.5rem 0.75rem; }

        /* Mensajes / alerts */
        .stAlert { padding-top: 0.5rem; padding-bottom: 0.5rem; }

        /* Tablas */
        .stDataFrame [role="row"] { height: 26px; }
        </style>
        """,
        unsafe_allow_html=True,
    )



def render_density_controls() -> None:
    _inject_max_width_css()
    """Renderiza selector de densidad y aplica CSS segun eleccion."""
    with st.sidebar:
        density = st.radio(
            "Densidad de UI",
            options=["Normal", "Compacta"],
            index=(1 if st.session_state.get("ui_density") == "Compacta" else 0),
            help="Compacta reduce espacios, margenes y tamano de controles.",
            key="ui_density_selector",
        )
    st.session_state["ui_density"] = density
    if density == "Compacta":
        _inject_compact_css()


# --- Toast/Notificación de error ---
def show_error_toast(msg: str, *, duration: int = 3) -> None:
    """Muestra notificación de error tipo toast en Streamlit."""
    st.error(msg, icon="🚨")
    st.markdown(
        f"<script>setTimeout(() => {{document.querySelectorAll('.stAlert').forEach(e => e.style.display='none');}}, {duration*1000});</script>",
        unsafe_allow_html=True,
    )


