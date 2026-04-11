"""Cargador centralizado de agentes IA.

Reemplaza las 4 copias de `_get_agent_suite()` que existían en cada página.
Punto único de acceso: importar `get_agent_suite` desde aquí.
"""

from __future__ import annotations

import os
from typing import Dict, Any

import streamlit as st

from src.ai_agent.seismic_interpreter import load_agent_suite
from src.ai_agent.dynamic_config import get_dynamic_config_path


def get_agent_suite() -> Dict[str, Any]:
    """Retorna el diccionario de agentes IA para el modelo activo.

    - Lee el modelo seleccionado desde `st.session_state["selected_ai_model"]`.
    - Propaga `LMSTUDIO_BASE_URL` si el modelo es de LM Studio.
    - Usa caché en `st.session_state` para no reinstanciar en cada rerun.
    - Solo almacena en caché si la carga fue exitosa (evita caché envenenado).

    Returns:
        Dict con los agentes, o dict vacío si hay error de configuración.
    """
    selected_model = st.session_state.get(
        "selected_ai_model", "nvidia/nemotron-3-super-120b-a12b:free"
    )

    # Propagar URL de LM Studio si aplica
    if selected_model.startswith("lmstudio:"):
        os.environ["LMSTUDIO_BASE_URL"] = st.session_state.get(
            "lmstudio_base_url", "http://127.0.0.1:1234/v1"
        )

    cache_key = f"ai_agents_{selected_model.replace('/', '_').replace(':', '_')}"
    cached = st.session_state.get(cache_key)
    if cached:
        return cached

    try:
        agents = load_agent_suite(get_dynamic_config_path(selected_model))
    except Exception as exc:
        st.session_state["ai_agents_error"] = str(exc)
        return {}

    if agents:
        st.session_state[cache_key] = agents
        st.session_state.pop("ai_agents_error", None)

    return agents or {}
