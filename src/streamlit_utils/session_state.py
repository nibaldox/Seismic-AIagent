
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
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional
import streamlit as st

LOGGER = logging.getLogger(__name__)

class SessionKeys(str, Enum):
    """Claves canónicas para session.metadata. Evita magic strings dispersos."""
    CURRENT_STREAM_NAME = "current_stream_name"
    SELECTED_TRACE_LABEL = "selected_trace_label"
    SELECTED_TRACE_INDEX = "selected_trace_index"
    STREAM_SUMMARIES = "stream_summaries"
    STREAMS = "streams"
    TRACE_CACHE = "trace_cache"


# --- API pública ---
__all__ = [
    "SessionKeys",
    "SeismicSession",
    "get_session",
    "mark_pipeline_step",
    "get_pipeline_steps",
    "pop_evicted_datasets",
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
    # Validaciones pre-análisis
    "validate_picks_consistency",
    "validate_localization_ready",
    # QC por dataset
    "set_qc_results",
    "get_qc_results",
    # Caché espectral por dataset (HVSR, RotD50, espectro respuesta)
    "set_spectral_cache",
    "get_spectral_cache",
    # IMs por dataset
    "set_ims_cache",
    "get_ims_cache",
    # AI history
    "add_ai_history_entry",
    "list_ai_history",
    "clear_ai_history",
]

# --- Caché temporal para streams (no serializable por Streamlit) ---
# Usa st.cache_resource para que el dict persista entre reruns de página
# dentro del mismo proceso del servidor (incluso tras hot-reload de archivos).
# LRU con límite de 10 entradas para evitar OOM con el Batch Loader.
_STREAM_CACHE_MAX = 10

from collections import OrderedDict as _OrderedDict


def _get_stream_store() -> "_OrderedDict[str, Any]":
    """Devuelve el dict LRU compartido vía st.cache_resource.

    El decorador @st.cache_resource garantiza que el mismo objeto se retorna
    en TODOS los reruns de todas las páginas dentro del mismo proceso Streamlit,
    lo que evita pérdidas de caché al navegar entre páginas.
    """
    try:
        import streamlit as _st

        @_st.cache_resource
        def _make_store():
            return _OrderedDict()

        return _make_store()
    except Exception:
        # Fallback si Streamlit no está disponible (tests, scripts)
        return _OrderedDict()


# Referencia al store — se obtiene en tiempo de ejecución para aprovechar
# el cache_resource de Streamlit. La variable se inicializa la primera vez
# que cualquier función la necesite.
_STREAM_CACHE: "_OrderedDict[str, Any] | None" = None

# Lista de nombres de datasets expulsados por LRU (se limpia al leer)
_EVICTED_DATASETS: "List[str]" = []


def pop_evicted_datasets() -> "List[str]":
    """Retorna y limpia la lista de datasets expulsados del caché LRU.

    Llamar en la UI para mostrar un aviso al usuario cuando un dataset
    fue expulsado automáticamente por límite de caché.
    """
    global _EVICTED_DATASETS
    evicted = list(_EVICTED_DATASETS)
    _EVICTED_DATASETS.clear()
    return evicted


def _cache() -> "_OrderedDict[str, Any]":
    """Retorna el dict LRU, inicializándolo si es necesario."""
    global _STREAM_CACHE
    if _STREAM_CACHE is None:
        _STREAM_CACHE = _get_stream_store()
    return _STREAM_CACHE


def _get_stream_from_cache(name: str) -> Optional[Any]:
    """Obtiene un stream del caché LRU. Mueve al final (más reciente)."""
    store = _cache()
    if name in store:
        store.move_to_end(name)
        return store[name]
    return None


def _store_stream_in_cache(name: str, stream: Any) -> None:
    """Guarda un stream en el caché LRU. Expulsa el más antiguo si hay >10."""
    global _EVICTED_DATASETS
    store = _cache()
    store[name] = stream
    store.move_to_end(name)
    while len(store) > _STREAM_CACHE_MAX:
        evicted_name, _ = store.popitem(last=False)
        _EVICTED_DATASETS.append(evicted_name)
        LOGGER.warning(
            "Dataset '%s' expulsado del caché LRU (límite=%d). "
            "Recárgalo si necesitas acceder a él.",
            evicted_name, _STREAM_CACHE_MAX,
        )


def _clear_stream_cache() -> None:
    """Limpia el caché temporal de streams."""
    _cache().clear()

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
    selected_ai_model: Optional[str] = None
    # Pipeline V0→V3: pasos completados para el dataset activo
    pipeline_steps: List[str] = field(default_factory=list)
    # Almacenamiento per-dataset: picks, pipeline_steps, ai_results, qc, spectral, ims
    per_dataset: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    # Historial de resultados IA — permite comparar análisis entre ejecuciones
    ai_history: List[Dict[str, Any]] = field(default_factory=list)


# --- Helpers para pipeline V0/V1/V2/V3 ---

def mark_pipeline_step(step: str, session: Optional["SeismicSession"] = None) -> None:
    """Marca un paso del pipeline como completado (p.ej. 'V1_baseline')."""
    session = session or get_session()
    if step not in session.pipeline_steps:
        session.pipeline_steps.append(step)


def get_pipeline_steps(session: Optional["SeismicSession"] = None) -> List[str]:
    session = session or get_session()
    return list(session.pipeline_steps)


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
    except Exception as exc:
        LOGGER.debug("get_session fallback: %s", exc)
        session = SeismicSession()
        try:
            st.session_state["seismo_session"] = session
        except Exception as exc2:
            LOGGER.debug("No se pudo guardar sesión en st.session_state: %s", exc2)
        return session


# --- Helpers para Equipo IA / Telemetria ---
def set_team_telemetry_context(*, time_range: str | None, columns: list[str] | None, df_head_md: str | None, notes: str | None, meta: Dict[str, Any] | None = None, filename: str | None = None) -> None:
    import datetime as _dt
    session = get_session()
    session.team_context["time_range"] = time_range
    session.team_context["telemetry"] = {
        "columns": columns or [],
        "df_head": df_head_md or "",
        "notes": notes,
        "meta": meta or {},
        "filename": filename,
        "analysis_ts": _dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "params": notes,
    }


def get_team_context() -> Dict[str, Any]:
    return get_session().team_context or {}


def register_stream(*, stream: Any, name: str, summary: Optional[str] = None) -> SeismicSession:
    """Registra un stream en el estado de sesion y lo marca como actual."""

    session = get_session()
    metadata = session.metadata
    
    # Guardar en caché temporal no serializable para evitar problemas UTCDateTime
    _store_stream_in_cache(name, stream)
    
    # Solo guardar el nombre en metadata (serializable)
    streams = metadata.setdefault("streams", {})
    streams[name] = name  # Solo el nombre, no el objeto completo
    
    summaries = metadata.setdefault("stream_summaries", {})
    if summary is not None:
        summaries[name] = summary

    _apply_current_stream(session=session, name=name, stream=stream, summary=summary)
    return session


def get_current_stream(session: Optional[SeismicSession] = None) -> Optional[Any]:
    session = session or get_session()
    
    # Obtener desde caché temporal no serializable
    current_name = session.metadata.get("current_stream_name")
    if current_name:
        return _get_stream_from_cache(current_name)
    
    return None


def get_current_stream_name(session: Optional[SeismicSession] = None) -> Optional[str]:
    session = session or get_session()
    return session.metadata.get("current_stream_name")


def list_dataset_names(session: Optional[SeismicSession] = None) -> List[str]:
    session = session or get_session()
    streams = session.metadata.get("streams", {})
    return list(streams.keys())


def set_current_stream(name: str, session: Optional[SeismicSession] = None) -> Optional[Any]:
    session = session or get_session()
    
    # Obtener desde caché temporal
    stream = _get_stream_from_cache(name)
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
            session.metadata["selected_trace_index"] = idx
            # NO guardar la traza completa para evitar problemas de serialización UTCDateTime
            # session.metadata["selected_trace"] = trace
            return trace

    return None


def get_selected_trace(session: Optional[SeismicSession] = None) -> Optional[Any]:
    session = session or get_session()
    
    # Reconstruir la traza desde el stream usando el índice guardado
    stream = get_current_stream(session)
    if stream is None:
        return None
        
    trace_index = session.metadata.get("selected_trace_index")
    if trace_index is not None:
        try:
            stream_list = list(stream)
            if 0 <= trace_index < len(stream_list):
                return stream_list[trace_index]
        except (IndexError, TypeError):
            pass
    
    # Fallback: usar etiqueta si el índice no funciona
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
    # NO guardar el stream directamente para evitar problemas de serialización UTCDateTime
    # metadata["current_stream"] = stream
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

    if previous != name:
        # Guardar el estado actual del dataset anterior antes de cambiar
        if previous is not None:
            store = _get_dataset_store(previous, session)
            store["picks"] = list(session.picks)
            store["pipeline_steps"] = list(session.pipeline_steps)
            store["ai_results"] = dict(session.ai_results)

        # Restaurar el estado del nuevo dataset (o inicializar vacío)
        new_store = _get_dataset_store(name, session)
        session.picks = list(new_store.get("picks", []))
        session.pipeline_steps = list(new_store.get("pipeline_steps", []))
        session.ai_results = dict(new_store.get("ai_results", {}))

    if not labels:
        metadata.pop("selected_trace_label", None)
        metadata.pop("selected_trace", None)  # Limpiar referencia antigua
        metadata.pop("selected_trace_index", None)
        return

    # Usar índices en lugar de guardar trazas completas para evitar problemas de serialización
    if selected_label in mapping and previous == name:
        # Encontrar el índice de la traza seleccionada
        for idx, (label, trace) in enumerate(mapping.items()):
            if label == selected_label:
                metadata["selected_trace_index"] = idx
                break
    else:
        metadata["selected_trace_label"] = labels[0]
        metadata["selected_trace_index"] = 0
    
    # Limpiar referencias antiguas a trazas completas y streams
    metadata.pop("selected_trace", None)
    metadata.pop("current_stream", None)


def validate_picks_consistency(session: Optional[SeismicSession] = None) -> List[str]:
    """Verifica que los picks sean físicamente coherentes.

    Comprueba para cada estación con par P/S que:
    - El tiempo P < tiempo S
    - La diferencia ts-tp es positiva

    Returns:
        Lista de mensajes de advertencia. Lista vacía = todo coherente.
    """
    session = session or get_session()
    picks = list(session.picks)
    warnings: List[str] = []

    # Agrupar por estación
    by_station: Dict[str, Dict[str, float]] = {}
    for p in picks:
        station = p.get("station", "UNK")
        phase = p.get("phase", "").upper().rstrip("?")
        if phase in ("P", "S"):
            by_station.setdefault(station, {})[phase] = float(p.get("time_rel", 0))

    for station, phases in by_station.items():
        if "P" in phases and "S" in phases:
            t_p = phases["P"]
            t_s = phases["S"]
            if t_p >= t_s:
                warnings.append(
                    f"Estación {station}: Pick P ({t_p:.2f}s) ≥ Pick S ({t_s:.2f}s). "
                    "El arribo P debe ser anterior al S."
                )
            elif (t_s - t_p) < 0.1:
                warnings.append(
                    f"Estación {station}: ts-tp = {t_s-t_p:.3f}s es muy pequeño "
                    "(< 0.1s). Verifica que los picks sean correctos."
                )

    return warnings


def validate_localization_ready(session: Optional[SeismicSession] = None) -> tuple:
    """Verifica que haya suficientes datos para ejecutar la localización 1D.

    Returns:
        Tuple (ready: bool, reasons: List[str]) donde reasons describe
        los problemas encontrados si ready=False.
    """
    session = session or get_session()
    picks = list(session.picks)
    reasons: List[str] = []

    if not picks:
        return False, ["No hay picks en sesión. Agrega picks P/S en el Waveform Viewer."]

    # Agrupar fases por estación
    by_station: Dict[str, Dict[str, float]] = {}
    for p in picks:
        station = p.get("station", "UNK")
        phase = p.get("phase", "").upper().rstrip("?")
        if phase in ("P", "S"):
            by_station.setdefault(station, {})[phase] = float(p.get("time_rel", 0))

    # Estaciones con par completo P+S válido
    valid_stations = []
    for station, phases in by_station.items():
        if "P" in phases and "S" in phases:
            if phases["S"] > phases["P"]:
                valid_stations.append(station)

    if len(valid_stations) == 0:
        reasons.append(
            "No se encontraron pares P/S válidos (con P < S). "
            "Se necesita al menos un par P/S por estación."
        )
        return False, reasons

    if len(valid_stations) < 3:
        reasons.append(
            f"Solo {len(valid_stations)} estación(es) con par P/S válido: {valid_stations}. "
            "Se recomiendan ≥ 3 estaciones para una localización confiable. "
            "El resultado con menos estaciones puede tener alta incertidumbre."
        )
        # No bloquear — permitir con 1-2 estaciones pero advertir
        return True, reasons

    return True, reasons


def _get_dataset_store(name: str, session: Optional[SeismicSession] = None) -> Dict[str, Any]:
    """Retorna (o crea) el dict de estado para un dataset específico."""
    session = session or get_session()
    per_dataset = getattr(session, "per_dataset", None)
    if per_dataset is None:
        session.per_dataset = {}
        per_dataset = session.per_dataset
    if name not in per_dataset:
        per_dataset[name] = {}
    return per_dataset[name]


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
        pass


# --- QC por dataset ---

def set_qc_results(dataset: str, results: Dict[str, Any], session: Optional[SeismicSession] = None) -> None:
    """Guarda los resultados de QC para un dataset específico."""
    store = _get_dataset_store(dataset, session)
    store["qc_results"] = results


def get_qc_results(dataset: str, session: Optional[SeismicSession] = None) -> Dict[str, Any]:
    """Recupera los resultados de QC para un dataset específico."""
    store = _get_dataset_store(dataset, session)
    return store.get("qc_results", {})


# --- Caché espectral por dataset (HVSR, RotD50, espectro respuesta) ---

def set_spectral_cache(dataset: str, key: str, data: Any, session: Optional[SeismicSession] = None) -> None:
    """Guarda un resultado espectral (hvsr_result, rotd_result, response_spec) por dataset."""
    store = _get_dataset_store(dataset, session)
    store.setdefault("spectral", {})[key] = data


def get_spectral_cache(dataset: str, key: str, session: Optional[SeismicSession] = None) -> Optional[Any]:
    """Recupera un resultado espectral por dataset y clave. Retorna None si no existe."""
    store = _get_dataset_store(dataset, session)
    return store.get("spectral", {}).get(key)


# --- IMs por dataset ---

def set_ims_cache(dataset: str, df: Any, session: Optional[SeismicSession] = None) -> None:
    """Guarda la tabla de IMs calculada para un dataset."""
    store = _get_dataset_store(dataset, session)
    store["ims_df"] = df


def get_ims_cache(dataset: str, session: Optional[SeismicSession] = None) -> Optional[Any]:
    """Recupera la tabla de IMs para un dataset. Retorna None si no existe."""
    store = _get_dataset_store(dataset, session)
    return store.get("ims_df")


# ── AI History ────────────────────────────────────────────────────────────────

def add_ai_history_entry(
    key: str,
    content: str,
    *,
    agent: Optional[str] = None,
    model: Optional[str] = None,
    duration_s: Optional[float] = None,
    session: Optional[SeismicSession] = None,
) -> None:
    """Registra una entrada en el historial IA.

    Args:
        key: Identificador del resultado (ej. ``waveform_analysis``,
            ``team_coordinate``, ``qc_agent``).
        content: Contenido markdown devuelto por el agente.
        agent: Nombre del agente que generó el resultado.
        model: Modelo utilizado (ej. ``deepseek/deepseek-chat-v3``).
        duration_s: Tiempo de ejecución en segundos.
    """
    session = session or get_session()
    import datetime

    entry: Dict[str, Any] = {
        "key": key,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "content": content,
    }
    if agent:
        entry["agent"] = agent
    if model:
        entry["model"] = model
    if duration_s is not None:
        entry["duration_s"] = round(duration_s, 2)

    # Inicializar historial si no existe (compatibilidad con sesiones activas)
    if not hasattr(session, "ai_history") or session.ai_history is None:
        session.ai_history = []
    session.ai_history.append(entry)

    # Mantener máximo 50 entradas para evitar crecimiento indefinido
    if len(session.ai_history) > 50:
        session.ai_history = session.ai_history[-50:]


def list_ai_history(
    *,
    key: Optional[str] = None,
    limit: int = 20,
    session: Optional[SeismicSession] = None,
) -> List[Dict[str, Any]]:
    """Retorna entradas del historial IA.

    Args:
        key: Filtrar por clave de resultado. Si es None retorna todas.
        limit: Máximo de entradas a retornar (default 20, más recientes).
        session: Sesión override.

    Returns:
        Lista de entradas ordenadas de más reciente a más antigua.
    """
    session = session or get_session()
    history = getattr(session, "ai_history", []) or []
    if key:
        history = [e for e in history if e.get("key") == key]
    return list(reversed(history))[-limit:]


def clear_ai_history(session: Optional[SeismicSession] = None) -> None:
    """Limpia todo el historial IA de la sesión."""
    session = session or get_session()
    session.ai_history = []
