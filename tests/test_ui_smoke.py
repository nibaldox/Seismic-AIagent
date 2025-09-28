"""
Smoke test de integración UI
"""
import streamlit as st

def test_ui_smoke():
    # Verifica que la app principal se puede importar y ejecutar main()
    import streamlit_app
    assert hasattr(streamlit_app, "main")
