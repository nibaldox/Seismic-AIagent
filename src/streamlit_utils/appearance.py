
"""Utilidades de apariencia/UX compartidas (densidad, estilos)."""

from __future__ import annotations
from pathlib import Path
import streamlit as st


def _load_custom_css() -> None:
    """Carga el CSS personalizado desde el archivo theme.css."""
    css_file = Path(__file__).resolve().parent.parent.parent / "assets" / "css" / "theme.css"
    if css_file.exists():
        with open(css_file) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def _inject_max_width_css(max_width: int = 1500) -> None:
    """Ajusta el ancho maximo del contenedor principal."""
    st.markdown(
        f"""
        <style>
        /* Debug: agregar borde temporal para verificar ancho */
        .main .block-container {{
            max-width: {max_width}px !important;
            margin: 0 auto !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            border: 2px solid red !important;
            box-sizing: border-box !important;
        }}
        
        /* Contenedor de la app principal - permitir full width */
        .stApp {{
            max-width: none !important;
        }}
        
        /* Elemento main section */
        section.main {{
            max-width: none !important;
        }}
        
        /* Contenedor específico del contenido */
        .main > div.block-container {{
            max-width: {max_width}px !important;
            margin-left: auto !important;
            margin-right: auto !important;
        }}
        
        /* Debug info */
        .main .block-container::before {{
            content: "Ancho máximo: {max_width}px";
            position: fixed;
            top: 10px;
            right: 10px;
            background: red;
            color: white;
            padding: 5px;
            z-index: 999999;
            font-size: 12px;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


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
    """Renderiza selector de densidad y aplica CSS segun eleccion."""
    # Cargar CSS personalizado primero
    _load_custom_css()
    
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
    
    # Aplicar ancho máximo DESPUÉS para que tenga prioridad
    _inject_max_width_css(1500)


# --- Toast/Notificación de error ---
def show_error_toast(msg: str, *, duration: int = 3) -> None:
    """Muestra notificación de error tipo toast en Streamlit."""
    st.error(msg, icon="🚨")
    st.markdown(
        f"<script>setTimeout(() => {{document.querySelectorAll('.stAlert').forEach(e => e.style.display='none');}}, {duration*1000});</script>",
        unsafe_allow_html=True,
    )


# --- Manejador de errores unificado ---
def handle_error(exc: Exception, *, context: str = "") -> None:
    """Muestra error con contexto y tipo en formato consistente."""
    try:
        # Intentar conversión segura del mensaje de error
        error_msg = str(exc)
        # Si contiene referencias a UTCDateTime, limpiar el mensaje
        if "UTCDateTime" in error_msg or "not JSON serializable" in error_msg:
            error_msg = "Error de serialización en análisis espectral (UTCDateTime)"
    except Exception:
        # Si hay error al convertir a string, usar tipo de error genérico
        error_msg = f"Error de tipo {type(exc).__name__}"
    
    msg = f"{context}: {error_msg}" if context else error_msg
    show_error_toast(msg, duration=5)


