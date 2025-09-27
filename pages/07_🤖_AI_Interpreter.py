"""AI interpreter interface."""

from __future__ import annotations

import os
from numbers import Number
from pathlib import Path
from typing import List

import streamlit as st
from dotenv import load_dotenv

# Load environment variables
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=False)

from src.ai_agent.earthquake_search import EarthquakeQuery, EarthquakeSearcher
from src.ai_agent.report_generator import build_report_agent, generate_markdown_report
from src.ai_agent.seismic_interpreter import load_agent_suite, run_primary_analysis
from src.streamlit_utils.session_state import (
    get_current_stream_name,
    get_session,
    get_traces_by_labels,
    get_selected_trace_label,
    list_dataset_names,
    list_trace_labels,
    set_current_stream,
)
from src.utils.config import load_yaml
from src.utils.logger import setup_logger

LOGGER = setup_logger(__name__)


def _get_agent_suite():
    if "ai_agents" not in st.session_state:
        st.session_state["ai_agents"] = load_agent_suite()
    return st.session_state["ai_agents"]


def _pick_default_labels(session, labels: List[str]) -> List[str]:
    if not labels:
        return []

    stored = session.metadata.get("ai_selected_trace_labels")
    if isinstance(stored, list):
        preserved = [label for label in stored if label in labels]
        if preserved:
            return preserved

    preferred = get_selected_trace_label(session=session)
    if preferred and preferred in labels:
        return [preferred]

    return [labels[0]]


def _build_trace_context(session, labels: List[str]) -> str:
    base_summary = session.stream_summary or ""
    traces = get_traces_by_labels(labels, session=session)
    if not traces:
        return base_summary

    lines = ["Selected trace snapshots:"]
    for label, trace in zip(labels, traces):
        stats = getattr(trace, "stats", None)
        if not stats:
            lines.append(f"- {label}")
            continue

        station = getattr(stats, "station", "?")
        channel = getattr(stats, "channel", "?")
        npts = getattr(stats, "npts", "?")
        delta = getattr(stats, "delta", None)
        sampling_rate = getattr(stats, "sampling_rate", None)
        start = getattr(stats, "starttime", None)

        duration = None
        if isinstance(npts, Number) and isinstance(delta, Number):
            duration = npts * delta

        parts = [f"station={station}", f"channel={channel}"]
        if sampling_rate:
            parts.append(f"fs={sampling_rate} Hz")
        elif delta:
            parts.append(f"Δ={delta} s")
        if duration:
            parts.append(f"duration≈{duration:.2f} s")
        parts.append(f"samples={npts}")
        if start:
            parts.append(f"start={start}")

        lines.append(f"- {label}: " + ", ".join(str(item) for item in parts if item))

    contextual = "\n".join(lines)
    if base_summary:
        return f"{base_summary}\n\n{contextual}"
    return contextual


def _parse_float(value) -> float | None:
    try:
        if value is None:
            return None
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _kelunji_coordinates(session) -> tuple[float | None, float | None, float | None]:
    metadata = session.metadata.get("kelunji_last") if session else None
    if not isinstance(metadata, dict):
        return None, None, None
    return (
        _parse_float(metadata.get("lat")),
        _parse_float(metadata.get("long")),
        _parse_float(metadata.get("alt")),
    )


def main() -> None:
    st.header("🤖 AI Seismic Interpreter")
    session = get_session()

    if not session or not session.stream_summary:
        st.info("Upload and visualize a seismic dataset before running the AI interpreter.")
        return

    dataset_names = list_dataset_names(session=session)
    current_dataset = get_current_stream_name(session=session)
    if dataset_names:
        selected_dataset = st.selectbox(
            "Active dataset",
            options=dataset_names,
            index=dataset_names.index(current_dataset) if current_dataset in dataset_names else 0,
            key="ai_active_dataset",
        )
        if selected_dataset and selected_dataset != current_dataset:
            set_current_stream(selected_dataset, session=session)
            current_dataset = selected_dataset

    agents = _get_agent_suite()
    labels = list_trace_labels(session=session)
    if not labels:
        st.info("No active traces detected. Please review your dataset in the waveform viewer.")
        return

    default_labels = _pick_default_labels(session, labels)
    selected_labels = st.multiselect(
        "Choose traces for AI interpretation",
        options=labels,
        default=default_labels,
        help="Select one or more traces to enrich the AI prompt.",
    )

    if selected_labels:
        session.metadata["ai_selected_trace_labels"] = selected_labels
        st.caption(f"Dataset: {session.dataset_name or 'Unnamed dataset'}")
        preview = get_traces_by_labels(selected_labels, session=session)
        if preview:
            with st.expander("Selected trace stats", expanded=False):
                for label, trace in zip(selected_labels, preview):
                    st.markdown(f"**{label}**")
                    st.code(str(getattr(trace, "stats", trace)), language="text")
    else:
        st.warning("Select at least one trace to enable AI interpretation.")

    config = load_yaml("agno_config.yaml").get("seismic_interpreter", {})
    st.subheader("AI Analysis")

    if st.button("🚀 Run AI Interpretation", disabled=not selected_labels):
        prompt_summary = _build_trace_context(session, selected_labels)
        with st.spinner("Running AI agents..."):
            analysis = run_primary_analysis(agents, prompt_summary)
            session.ai_results["analysis"] = analysis
        if not analysis:
            st.warning("AI analysis not available. Check agent configuration.")

    if session.ai_results.get("analysis"):
        st.markdown(session.ai_results["analysis"])

    st.subheader("Earthquake Context")

    kelunji_lat, kelunji_lon, kelunji_alt = _kelunji_coordinates(session)
    stored_lat = session.metadata.get("earthquake_search_lat") if session else None
    stored_lon = session.metadata.get("earthquake_search_lon") if session else None

    if stored_lat is None and kelunji_lat is not None:
        stored_lat = kelunji_lat
        session.metadata["earthquake_search_lat"] = stored_lat
    if stored_lon is None and kelunji_lon is not None:
        stored_lon = kelunji_lon
        session.metadata["earthquake_search_lon"] = stored_lon

    col1, col2 = st.columns(2)
    with col1:
        lat = st.number_input(
            "Latitude",
            value=float(stored_lat) if stored_lat is not None else 0.0,
            min_value=-90.0,
            max_value=90.0,
            format="%.5f",
        )
    with col2:
        lon = st.number_input(
            "Longitude",
            value=float(stored_lon) if stored_lon is not None else 0.0,
            min_value=-180.0,
            max_value=180.0,
            format="%.5f",
        )

    session.metadata["earthquake_search_lat"] = lat
    session.metadata["earthquake_search_lon"] = lon

    if kelunji_lat is not None and kelunji_lon is not None:
        st.caption("Coordenadas precargadas desde metadatos Kelunji. Ajusta si lo necesitas.")

    default_radius = session.metadata.get("earthquake_search_radius_km", 100)
    radius = st.slider(
        "Search radius (km)",
        min_value=10,
        max_value=500,
        value=int(default_radius) if isinstance(default_radius, (int, float)) else 100,
        step=10,
    )
    session.metadata["earthquake_search_radius_km"] = radius

    if st.button("🔍 Fetch Nearby Events"):
        searcher = EarthquakeSearcher(
            os.getenv("USGS_API_URL", "https://earthquake.usgs.gov/fdsnws/event/1/"),
            os.getenv("EMSC_API_URL", "https://www.seismicportal.eu/fdsnws/event/1/"),
        )
        query = EarthquakeQuery(latitude=lat, longitude=lon, radius_km=radius)
        results = searcher.search_all(query)
        summary = searcher.summarize_results(results)
        session.ai_results["earthquakes"] = summary
        st.markdown(summary)
    elif session.ai_results.get("earthquakes"):
        st.markdown(session.ai_results["earthquakes"])

    st.subheader("Automated Report")
    if st.button("📝 Generate Report", disabled=not session.ai_results.get("analysis")):
        default_model = config.get("default_model", {})
        report_agent = build_report_agent(
            default_model.get("provider", "openrouter"),
            default_model.get("id", "deepseek/deepseek-chat-v3.1:free"),
        )
        report = generate_markdown_report(
            report_agent,
            waveform_summary=session.stream_summary,
            ai_analysis=session.ai_results.get("analysis"),
            earthquake_context=session.ai_results.get("earthquakes"),
        )
        session.ai_results["report"] = report
        st.download_button(
            "⬇️ Download Markdown",
            data=report,
            file_name="seismic_report.md",
            mime="text/markdown",
        )
        st.markdown(report)
    elif session.ai_results.get("report"):
        st.download_button(
            "⬇️ Download Markdown",
            data=session.ai_results["report"],
            file_name="seismic_report.md",
            mime="text/markdown",
        )
        st.markdown(session.ai_results["report"])


if __name__ == "__main__":  # pragma: no cover
    main()
