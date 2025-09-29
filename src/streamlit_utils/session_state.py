
"""
Utilidades para manejar el estado de sesión de Streamlit.

Este módulo centraliza toda la gestión de estado compartido entre páginas:
- Sesión principal y metadatos
- Selección y registro de streams/trazas
- Picks P/S y contexto para equipo IA
- Caché ligera de arrays de traza
- Persistencia de datos de histogramas
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional
import streamlit as st

# --- API pública ---
__all__ = [
    "SeismicSession",
    "get_session",
    # Caché de trazas
    "set_trace_cache",
    "get_trace_cache",
    "clear_trace_cache",
    # Picks
    "add_pick",
    "list_picks",
    "clear_picks",
    # Streams y trazas
    "register_stream",
    "get_current_stream",
    "get_current_stream_name",
    "list_dataset_names",
    "set_current_stream",
    "get_stream_summary",
    "list_trace_labels",
    "set_selected_trace",
    "get_selected_trace",
    "get_selected_trace_label",
    "get_traces_by_labels",
    # Telemetría/Equipo IA
    "set_team_telemetry_context",
    "get_team_context",
    # Histogramas
    "set_histogram_data",
    "get_histogram_data",
    "clear_histogram_data",
]

# --- Memoización/caché de arrays de traza ---
def set_trace_cache(key: str, value: Any, session: Optional[SeismicSession] = None) -> None:
    session = session or get_session()
    session.metadata.setdefault("trace_cache", {})[key] = value

def get_trace_cache(key: str, session: Optional[SeismicSession] = None) -> Any:
    session = session or get_session()
    return session.metadata.get("trace_cache", {}).get(key)

def clear_trace_cache(session: Optional[SeismicSession] = None) -> None:
    session = session or get_session()
    session.metadata["trace_cache"] = {}


@dataclass

class SeismicSession:
    """Dataclass que encapsula los datos persistentes de la app."""
    dataset_name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    stream_summary: Optional[str] = None
    ai_results: Dict[str, Any] = field(default_factory=dict)
    picks: List[Dict[str, Any]] = field(default_factory=list)
    team_context: Dict[str, Any] = field(default_factory=dict)
    histogram_data: Optional[Any] = None  # DataFrame
    histogram_meta: Dict[str, Any] = field(default_factory=dict)
    histogram_filename: Optional[str] = None


def add_pick(*, phase: str, time_rel: float, station: str, channel: str, method: str = "manual", session: Optional[SeismicSession] = None) -> None:
    session = session or get_session()
    session.picks.append(
        {
            "phase": phase,
            "time_rel": float(time_rel),
            "station": station,
            "channel": channel,
            "method": method,
        }
    )


def list_picks(session: Optional[SeismicSession] = None) -> List[Dict[str, Any]]:
    session = session or get_session()
    return list(session.picks)


def clear_picks(session: Optional[SeismicSession] = None) -> None:
    session = session or get_session()
    session.picks.clear()


def get_session() -> SeismicSession:
    """Obtiene (o crea) la instancia de sesion principal."""

    try:
        session = st.session_state.get("seismo_session")
        if session is None:
            session = SeismicSession()
            st.session_state["seismo_session"] = session
        return session
    except Exception:
        # Fallback: create a new session if anything goes wrong
        session = SeismicSession()
        try:
            st.session_state["seismo_session"] = session
        except Exception:
            pass  # If even setting fails, just return the session
        return session


# --- Helpers para Equipo IA / Telemetria ---
def set_team_telemetry_context(*, time_range: str | None, columns: list[str] | None, df_head_md: str | None, notes: str | None, meta: Dict[str, Any] | None = None, filename: str | None = None) -> None:
    session = get_session()
    session.team_context["time_range"] = time_range
    session.team_context["telemetry"] = {
        "columns": columns or [],
        "df_head": df_head_md or "",
        "notes": notes,
        "meta": meta or {},
        "filename": filename,
    }


def get_team_context() -> Dict[str, Any]:
    return get_session().team_context or {}


def register_stream(*, stream: Any, name: str, summary: Optional[str] = None) -> SeismicSession:
    """Registra un stream en el estado de sesion y lo marca como actual."""

    session = get_session()
    metadata = session.metadata
    streams = metadata.setdefault("streams", {})
    streams[name] = stream
    summaries = metadata.setdefault("stream_summaries", {})
    if summary is not None:
        summaries[name] = summary

    _apply_current_stream(session=session, name=name, stream=stream, summary=summary)
    return session


def get_current_stream(session: Optional[SeismicSession] = None) -> Optional[Any]:
    session = session or get_session()
    return session.metadata.get("current_stream")


def get_current_stream_name(session: Optional[SeismicSession] = None) -> Optional[str]:
    session = session or get_session()
    return session.metadata.get("current_stream_name")


def list_dataset_names(session: Optional[SeismicSession] = None) -> List[str]:
    session = session or get_session()
    streams = session.metadata.get("streams", {})
    return list(streams.keys())


def set_current_stream(name: str, session: Optional[SeismicSession] = None) -> Optional[Any]:
    session = session or get_session()
    streams = session.metadata.get("streams", {})
    stream = streams.get(name)
    if stream is None:
        return None

    summaries = session.metadata.get("stream_summaries", {})
    summary = summaries.get(name)
    _apply_current_stream(session=session, name=name, stream=stream, summary=summary)
    return stream


def get_stream_summary(name: Optional[str] = None, session: Optional[SeismicSession] = None) -> Optional[str]:
    session = session or get_session()
    if name is None:
        return session.stream_summary

    summaries = session.metadata.get("stream_summaries", {})
    return summaries.get(name)


def list_trace_labels(
    session: Optional[SeismicSession] = None,
    stream: Optional[Iterable[Any]] = None,
) -> List[str]:
    """Devuelve etiquetas legibles para cada traza disponible."""

    if stream is None:
        stream = get_current_stream(session)
    if stream is None:
        return []

    labels: List[str] = []
    for idx, trace in enumerate(stream):
        labels.append(_trace_label(trace, idx))
    return labels


def set_selected_trace(label: str, session: Optional[SeismicSession] = None) -> Optional[Any]:
    """Selecciona una traza y la almacena para uso transversal."""

    session = session or get_session()
    stream = get_current_stream(session)
    if stream is None:
        return None

    for idx, trace in enumerate(stream):
        candidate = _trace_label(trace, idx)
        if candidate == label:
            session.metadata["selected_trace_label"] = candidate
            session.metadata["selected_trace"] = trace
            return trace

    return None


def get_selected_trace(session: Optional[SeismicSession] = None) -> Optional[Any]:
    session = session or get_session()
    trace = session.metadata.get("selected_trace")
    if trace is not None:
        return trace

    label = session.metadata.get("selected_trace_label")
    if not label:
        return None
    return set_selected_trace(label, session=session)


def get_selected_trace_label(session: Optional[SeismicSession] = None) -> Optional[str]:
    session = session or get_session()
    return session.metadata.get("selected_trace_label")


def get_traces_by_labels(labels: Iterable[str], session: Optional[SeismicSession] = None) -> List[Any]:
    """Obtiene las trazas asociadas a las etiquetas solicitadas."""

    session = session or get_session()
    stream = get_current_stream(session)
    if stream is None:
        return []

    mapping = {_trace_label(trace, idx): trace for idx, trace in enumerate(stream)}
    return [mapping[label] for label in labels if label in mapping]


def _apply_current_stream(*, session: SeismicSession, name: str, stream: Iterable[Any], summary: Optional[str]) -> None:
    metadata = session.metadata
    previous = metadata.get("current_stream_name")

    metadata["current_stream_name"] = name
    metadata["current_stream"] = stream
    session.dataset_name = name

    summaries = metadata.setdefault("stream_summaries", {})
    if summary is not None:
        summaries[name] = summary
    elif name in summaries:
        summary = summaries[name]

    if summary is not None:
        session.stream_summary = summary

    labels = list_trace_labels(session=session, stream=stream)
    selected_label = metadata.get("selected_trace_label")
    mapping = {_trace_label(trace, idx): trace for idx, trace in enumerate(stream)}

    if previous != name and session.ai_results:
        session.ai_results.clear()

    if not labels:
        metadata.pop("selected_trace_label", None)
        metadata.pop("selected_trace", None)
        return

    if selected_label in mapping and previous == name:
        metadata["selected_trace"] = mapping[selected_label]
    else:
        metadata["selected_trace_label"] = labels[0]
        metadata["selected_trace"] = mapping[labels[0]]


def _trace_label(trace: Any, idx: int) -> str:
    """Construye una etiqueta estable para la traza proporcionada."""

    if hasattr(trace, "id") and trace.id:
        return str(trace.id)
    if hasattr(trace, "stats") and hasattr(trace.stats, "station"):
        station = trace.stats.station
        channel = getattr(trace.stats, "channel", f"CH{idx+1}")
        return f"{station}.{channel}" if station else f"Trace {idx+1}"
    return f"Trace {idx+1}"


# --- Helpers para Histogramas ---
def set_histogram_data(*, df: Any, meta: Dict[str, Any], filename: Optional[str] = None, session: Optional[SeismicSession] = None) -> None:
    """Guarda los datos de histogramas en el estado de sesion."""
    session = session or get_session()
    session.histogram_data = df
    session.histogram_meta = meta
    session.histogram_filename = filename


def get_histogram_data(session: Optional[SeismicSession] = None) -> tuple[Optional[Any], Dict[str, Any], Optional[str]]:
    """Recupera los datos de histogramas del estado de sesion."""
    session = session or get_session()
    # Manejar sesiones existentes que no tienen los nuevos atributos
    try:
        return getattr(session, 'histogram_data', None), getattr(session, 'histogram_meta', {}), getattr(session, 'histogram_filename', None)
    except AttributeError:
        # Si la sesion no tiene los atributos, devolver valores por defecto
        return None, {}, None


def clear_histogram_data(session: Optional[SeismicSession] = None) -> None:
    """Limpia los datos de histogramas del estado de sesion."""
    session = session or get_session()
    try:
        session.histogram_data = None
        session.histogram_meta = {}
        session.histogram_filename = None
    except AttributeError:
        # Si la sesion no tiene los atributos, no hacer nada
        pass
