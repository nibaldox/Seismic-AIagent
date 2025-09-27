"""Main entry point for SeismoAnalyzer Pro."""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from src.streamlit_utils.session_state import get_session

PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG_DIR = PROJECT_ROOT / "config"

load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=False)

st.set_page_config(
    page_title="SeismoAnalyzer Pro",
    page_icon="🌋",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("SeismoAnalyzer Pro")

session = get_session()
st.session_state.setdefault("navigation", "Waveform Viewer")

st.sidebar.success("Navigate using the Streamlit pages menu on the left.")

st.write(
    "Welcome to the Rapid Seismic Analyzer. Use the sidebar to upload data, "
    "explore waveforms, and access AI-powered interpretation tools."
)

st.markdown(
    """
    ### Quick Start
    1. Open the **📁 Upload** page to load MiniSEED or SAC files.
    2. Explore the **📊 Waveform Viewer** for interactive plots.
    3. Visit **🤖 AI Interpreter** once data is loaded for automated insights.
    """
)

st.info(
    "Configuration files are located in `config/`. Adjust `agno_config.yaml` to fine-tune "
    "the agent model selection strategy."
)

if os.getenv("OPENROUTER_API_KEY"):
    st.success("OpenRouter API key detected – AI agent features ready.")
else:
    st.warning("Add API keys to `.env` to unlock full AI capabilities.")
