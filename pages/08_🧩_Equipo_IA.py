"""Página deprecada: Equipo IA.

Esta funcionalidad fue unificada en la página "🤖 AI Interpreter" con opciones avanzadas
para ejecutar el Equipo IA coordinado. Mantener esta página sólo muestra este aviso y
evita duplicar lógica.
"""

from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Equipo IA (deprecado)", page_icon="🧩")

st.header("🧩 Equipo IA – Página deprecada")
st.info(
    "La funcionalidad del Equipo IA fue integrada en la página '🤖 AI Interpreter'.\n"
    "Usa el radio 'Modo de análisis' para elegir 'Equipo IA (coordinado)' y, si deseas,\n"
    "activa las 'Opciones avanzadas' para incluir telemetría desde Histogramas."
)

col1, col2 = st.columns([1, 1])
with col1:
    if st.button("Ir a 🤖 AI Interpreter"):
        try:
            # Disponible en Streamlit recientes; si no existe, caemos al mensaje
            st.switch_page("pages/07_🤖_AI_Interpreter.py")  # type: ignore[attr-defined]
        except Exception:
            st.success("Abre '🤖 AI Interpreter' desde el menú lateral.")
            st.stop()

with col2:
    st.warning("Esta página será removida en una próxima limpieza de código.")
