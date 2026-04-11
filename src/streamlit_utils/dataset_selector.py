"""
Componente reutilizable para selección de dataset activo.

Centraliza la lógica de selectbox + set_current_stream + st.rerun()
para evitar duplicación en múltiples páginas.
"""

from __future__ import annotations
from typing import Optional

import streamlit as st

from src.streamlit_utils.session_state import (
    get_session,
    list_dataset_names,
    get_current_stream_name,
    set_current_stream,
)


def render_dataset_selector(
    key: str,
    label: str = "Dataset activo",
    show_if_single: bool = False,
) -> Optional[str]:
    """Renderiza un selectbox de dataset y aplica el cambio si hay selección nueva.

    Args:
        key: Clave única para el widget de Streamlit (evita colisiones entre páginas).
        label: Texto a mostrar sobre el selectbox.
        show_if_single: Si False (defecto), no muestra el widget cuando solo
            hay un dataset cargado (evita ruido visual innecesario).

    Returns:
        Nombre del dataset activo, o None si no hay datasets cargados.
    """
    session = get_session()
    dataset_names = list_dataset_names(session=session)

    if not dataset_names:
        st.info("No hay datasets cargados. Usa **Uploader** o **Batch Loader** para cargar datos.")
        return None

    if not show_if_single and len(dataset_names) == 1:
        # Un solo dataset: activarlo silenciosamente sin mostrar el widget
        current = get_current_stream_name(session=session)
        if current != dataset_names[0]:
            set_current_stream(dataset_names[0], session=session)
            st.rerun()
        return dataset_names[0]

    current = get_current_stream_name(session=session)
    try:
        current_idx = dataset_names.index(current) if current in dataset_names else 0
    except ValueError:
        current_idx = 0

    selected = st.selectbox(
        label,
        options=dataset_names,
        index=current_idx,
        key=key,
    )

    if selected and selected != current:
        set_current_stream(selected, session=session)
        st.rerun()

    return selected or current
