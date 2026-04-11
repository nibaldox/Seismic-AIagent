"""Pagina de estimacion de magnitud local ML Wood-Anderson.

Expone la funcionalidad de ``src/core/magnitude.py`` para que el usuario
pueda estimar la magnitud local ML mediante el metodo Wood-Anderson estandar
(Uhrhammer & Collins 1990) con correccion de respuesta instrumental opcional.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import streamlit as st
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=False)

# ---------------------------------------------------------------------------
# Page config (debe ir ANTES de cualquier otro comando de Streamlit)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Estimacion de Magnitud ML",
    page_icon="🔬",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Imports internos
# ---------------------------------------------------------------------------
from src.streamlit_utils.session_state import (
    get_current_stream,
    get_current_stream_name,
    list_picks,
    list_trace_labels,
    get_selected_trace,
)

try:
    from src.streamlit_utils.appearance import apply_theme  # type: ignore

    apply_theme()
except (ImportError, AttributeError):
    pass

from src.core.magnitude import (
    MagnitudeResult,
    estimate_local_magnitude_wa_with_response,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def _load_magnitude_config() -> dict:
    """Carga la calibracion regional desde agents_config.yaml (cacheado)."""
    try:
        import yaml

        cfg_path = PROJECT_ROOT / "config" / "agents_config.yaml"
        if cfg_path.exists():
            with open(cfg_path, "r", encoding="utf-8") as fh:
                raw = yaml.safe_load(fh)
            return raw.get("magnitude_calibration", {})
    except Exception:
        pass
    return {}


def _active_region_description(cal: dict) -> str:
    """Retorna la descripcion de la region de calibracion activa."""
    active = cal.get("active_region", "hutton_boore_california")
    regions = cal.get("regions", {})
    desc = regions.get(active, {}).get("description", active)
    return f"{active} — {desc}"


def _run_magnitude_estimation(
    trace,
    picks: list,
    station: str,
    inventory_path: Optional[str],
) -> MagnitudeResult:
    """Ejecuta la estimacion de magnitud con la traza y picks provistos."""
    import numpy as np

    trace_data = np.asarray(trace.data, dtype=float)
    sr = float(trace.stats.sampling_rate)
    channel = getattr(trace.stats, "channel", "CH")
    network = getattr(trace.stats, "network", "XX")

    return estimate_local_magnitude_wa_with_response(
        picks=picks,
        trace_data=trace_data,
        trace_sampling_rate=sr,
        station=station,
        inventory_path=inventory_path if inventory_path else None,
        trace_stats=trace.stats,
        network=network,
        channel=channel,
    )


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("🔬 Estimacion de Magnitud Local ML")
st.markdown(
    """
    Calcula la **magnitud local (ML) Wood-Anderson** a partir de la traza seleccionada
    y los picks P/S previamente marcados.

    El metodo simula el desplazamiento que registraria un sismografo Wood-Anderson
    estandar (PAZ segun Uhrhammer & Collins, 1990) y aplica la funcion de calibracion
    regional para obtener ML.  La distancia epicentral se estima mediante la relacion
    de Wadati (Δt P-S).
    """
)
st.divider()

# ---------------------------------------------------------------------------
# Sidebar — controles
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Parametros")

    # Selector de traza
    trace_labels = list_trace_labels()
    if trace_labels:
        selected_label = st.selectbox(
            "Traza a analizar",
            options=trace_labels,
            index=0,
            help="Selecciona la componente sísmica para la estimacion de amplitud.",
        )
    else:
        selected_label = None

    st.divider()

    # Informacion de calibracion
    st.subheader("Calibracion regional")
    mag_cal = _load_magnitude_config()
    if mag_cal:
        region_info = _active_region_description(mag_cal)
        st.info(region_info, icon="📐")
        st.caption(
            "Para cambiar la region activa, edita `config/agents_config.yaml` "
            "→ `magnitude_calibration.active_region`."
        )
    else:
        st.warning(
            "No se encontro calibracion regional. Se usara Hutton & Boore (1987).",
            icon="⚠️",
        )

    st.divider()

    # Inventario instrumental (opcional)
    st.subheader("Respuesta instrumental (opcional)")
    inventory_path_input = st.text_input(
        "Ruta al inventario (StationXML / RESP)",
        value="",
        placeholder="ej. config/station.xml",
        help=(
            "Si tienes un archivo StationXML o RESP con la respuesta de tu sensor, "
            "indícalo aquí para mejorar la precision de ML. "
            "Deja vacío para usar heurísticas de canal."
        ),
    )
    inventory_path: Optional[str] = None
    if inventory_path_input.strip():
        candidate = Path(inventory_path_input.strip())
        if not candidate.is_absolute():
            candidate = PROJECT_ROOT / candidate
        if candidate.exists():
            inventory_path = str(candidate)
            st.success(f"Inventario encontrado: `{candidate.name}`", icon="✅")
        else:
            st.error(f"Archivo no encontrado: `{candidate}`", icon="❌")

# ---------------------------------------------------------------------------
# Guard: stream no cargado
# ---------------------------------------------------------------------------
stream = get_current_stream()
if stream is None:
    st.warning(
        "**No hay datos cargados.** "
        "Ve a la pagina **Batch Loader** o **Waveform Viewer** y carga un archivo sismico.",
        icon="📂",
    )
    st.stop()

stream_name = get_current_stream_name() or "desconocido"

# ---------------------------------------------------------------------------
# Guard: traza seleccionada
# ---------------------------------------------------------------------------
if not trace_labels or selected_label is None:
    st.error("No se encontraron trazas en el stream actual.", icon="❌")
    st.stop()

# Buscar la traza seleccionada en el stream
selected_trace = None
for idx, tr in enumerate(stream):
    label_candidate = (
        tr.id if (hasattr(tr, "id") and tr.id) else
        f"{tr.stats.station}.{tr.stats.channel}" if hasattr(tr, "stats") else
        f"Trace {idx + 1}"
    )
    if label_candidate == selected_label:
        selected_trace = tr
        break

if selected_trace is None:
    st.error(
        f"No se pudo recuperar la traza `{selected_label}`. "
        "Intenta recargar el archivo.",
        icon="❌",
    )
    st.stop()

# Extraer station de la traza
station_id = getattr(selected_trace.stats, "station", "UNK") if hasattr(selected_trace, "stats") else "UNK"

# ---------------------------------------------------------------------------
# Info del dataset activo
# ---------------------------------------------------------------------------
st.caption(f"Dataset activo: **{stream_name}** | Traza: **{selected_label}** | Estacion: **{station_id}**")

# ---------------------------------------------------------------------------
# Guard: picks P y S
# ---------------------------------------------------------------------------
all_picks = list_picks()
p_picks = [p for p in all_picks if p.get("phase") == "P"]
s_picks = [p for p in all_picks if p.get("phase") == "S"]

if not all_picks:
    st.warning(
        "**No hay picks cargados.** "
        "Para estimar ML necesitas al menos un pick P y un pick S. "
        "Ve a la pagina **Waveform Viewer** y marca las fases P y S manualmente "
        "o activa el picker automatico STA/LTA.",
        icon="📍",
    )
    st.stop()

if not p_picks:
    st.warning(
        "**Falta el pick P.** Ve a **Waveform Viewer** y marca la fase P.",
        icon="⚠️",
    )
    st.stop()

if not s_picks:
    st.warning(
        "**Falta el pick S.** Ve a **Waveform Viewer** y marca la fase S.",
        icon="⚠️",
    )
    st.stop()

# ---------------------------------------------------------------------------
# Tabla de picks
# ---------------------------------------------------------------------------
import pandas as pd

st.subheader("Picks disponibles")
df_picks = pd.DataFrame(all_picks)[["phase", "time_rel", "station", "channel", "method"]]
df_picks.columns = ["Fase", "Tiempo relativo (s)", "Estacion", "Canal", "Metodo"]
df_picks["Tiempo relativo (s)"] = df_picks["Tiempo relativo (s)"].map(lambda x: f"{float(x):.3f}")
st.dataframe(df_picks, use_container_width=True, hide_index=True)

# Advertencia si los picks no coinciden con la estacion de la traza
picks_for_station = [p for p in all_picks if p.get("station") == station_id]
if not picks_for_station:
    st.info(
        f"Nota: Ninguno de los picks tiene `station='{station_id}'`. "
        f"La funcion de magnitud buscara picks con esa estacion. "
        "Verifica que los picks fueron generados desde esta misma traza.",
        icon="ℹ️",
    )

st.divider()

# ---------------------------------------------------------------------------
# Boton de estimacion
# ---------------------------------------------------------------------------
st.subheader("Calcular magnitud ML")

col_btn, col_spacer = st.columns([1, 3])
with col_btn:
    run_estimation = st.button(
        "Estimar Magnitud ML",
        type="primary",
        use_container_width=True,
        help="Ejecuta la estimacion Wood-Anderson con la traza y picks actuales.",
    )

if run_estimation:
    with st.spinner("Calculando magnitud Wood-Anderson..."):
        try:
            result: MagnitudeResult = _run_magnitude_estimation(
                trace=selected_trace,
                picks=all_picks,
                station=station_id,
                inventory_path=inventory_path,
            )
        except Exception as exc:
            st.error(f"Error durante la estimacion: {exc}", icon="❌")
            st.stop()

    # ------------------------------------------------------------------
    # Metricas
    # ------------------------------------------------------------------
    st.subheader("Resultado")

    if result.ml is not None:
        uncertainty_str = (
            f"±{result.ml_uncertainty:.1f}" if result.ml_uncertainty is not None else ""
        )
        ml_display = f"{result.ml:.2f} {uncertainty_str}".strip()
    else:
        ml_display = "N/D"

    amplitude_display = (
        f"{result.amplitude_mm:.4f} mm" if result.amplitude_mm is not None else "N/D"
    )
    delta_ps_display = (
        f"{result.delta_ps:.2f} s" if result.delta_ps is not None else "N/D"
    )
    distance_display = (
        f"{result.distance_km:.1f} km" if result.distance_km is not None else "N/D"
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        label="Magnitud Local ML",
        value=ml_display,
        help="Magnitud local Wood-Anderson. La incertidumbre refleja ausencia de respuesta instrumental y uso de una sola estacion.",
    )
    col2.metric(
        label="Amplitud WA",
        value=amplitude_display,
        help="Amplitud pico-a-pico equivalente en el sismografo Wood-Anderson simulado.",
    )
    col3.metric(
        label="Δt P-S",
        value=delta_ps_display,
        help="Diferencia de tiempos de arribo S - P en segundos.",
    )
    col4.metric(
        label="Distancia estimada",
        value=distance_display,
        help="Distancia hipocentral estimada por la relacion de Wadati (k=8.4 km/s, modelo cortical andino).",
    )

    # ------------------------------------------------------------------
    # Indicador de respuesta instrumental
    # ------------------------------------------------------------------
    if result.instrument_response_removed:
        st.success(
            "Respuesta instrumental removida correctamente.",
            icon="✅",
        )
    else:
        st.warning(
            "Respuesta instrumental NO removida. La amplitud Wood-Anderson es aproximada. "
            "La incertidumbre en ML puede ser hasta ±1.0 unidades.",
            icon="⚠️",
        )

    # ------------------------------------------------------------------
    # Notas del metodo
    # ------------------------------------------------------------------
    if result.notes:
        st.caption(f"Metodo: {result.notes}")
    if result.method:
        st.caption(f"Identificador de metodo: `{result.method}`")
    if result.units_assumed:
        st.caption(f"Unidades de entrada asumidas: `{result.units_assumed}`")

    # ------------------------------------------------------------------
    # Warnings del resultado
    # ------------------------------------------------------------------
    if result.warnings:
        st.divider()
        st.subheader("Notas y advertencias del calculo")
        for w in result.warnings:
            # Clasificar por prefijo para decidir el tipo de alerta
            w_clean = w.strip()
            if w_clean.startswith("✓") or "exitosamente" in w_clean.lower():
                st.info(w_clean, icon="ℹ️")
            elif (
                w_clean.startswith("⚠")
                or "IMPORTANTE" in w_clean
                or "error" in w_clean.lower()
                or "faltan" in w_clean.lower()
            ):
                st.warning(w_clean, icon="⚠️")
            else:
                st.info(w_clean, icon="📝")

    # ------------------------------------------------------------------
    # Sin resultado
    # ------------------------------------------------------------------
    if result.ml is None:
        st.error(
            "No fue posible calcular ML. Revisa los picks y la traza seleccionada. "
            f"Razon: {result.notes}",
            icon="❌",
        )

# ---------------------------------------------------------------------------
# Seccion expandible: interpretacion de resultados
# ---------------------------------------------------------------------------
with st.expander("Como interpretar los resultados", expanded=False):
    st.markdown(
        """
        ### Magnitud local ML Wood-Anderson

        **Definicion:**
        ML fue definida por C. F. Richter (1935) como el logaritmo en base 10 de la amplitud
        maxima (en milesimas de milimetro) registrada por un sismografo Wood-Anderson estandar
        a 100 km de distancia epicentral.

        **Formula aplicada:**
        ```
        ML = log10(A_mm) - log10(A0(R))
        ```
        donde `A_mm` es la amplitud pico en el sismografo Wood-Anderson simulado
        y `log10(A0(R))` es la funcion de calibracion regional (termino de correccion por
        atenuacion geometrica y anelastica).

        **Funcion de calibracion activa:**
        - Chile — zona de subduccion Nazca/Sudamerica (CSN, Univ. de Chile).
        - Coeficientes basados en Barrientos (1980) y calibraciones operativas del
          Centro Sismologico Nacional.
        - Para cambiar a otra region, edita `config/agents_config.yaml`.

        **Estimacion de distancia:**
        La distancia hipocentral se estima mediante la relacion de Wadati:
        ```
        R = k * (ts - tp)   con k = 8.4 km/s
        ```
        Este valor de k corresponde a Vp=6.0 km/s, Vs=3.5 km/s, modelo cortical andino.
        La incertidumbre en la distancia con una sola estacion es tipicamente ±20-30%.

        **Respuesta instrumental:**
        Cuando no se provee un inventario StationXML, se aplican heuristicas basadas en el
        codigo de canal para inferir las unidades (m/s², cm/s², m/s, m) y se simula el
        sismografo Wood-Anderson directamente. Esto introduce una incertidumbre adicional
        de hasta ±1.0 unidades en ML.

        **Limitaciones importantes:**
        - Esta es una estimacion de estacion unica. Las redes sismologicas promedian ML
          sobre multiples estaciones.
        - La magnitud preliminar puede diferir ±0.3-0.5 unidades respecto a catalogos
          oficiales incluso con respuesta instrumental correcta.
        - Para reportes oficiales, valida con el Centro Sismologico Nacional (csn.uchile.cl)
          o la agencia nacional correspondiente.

        **Escala de referencia rapida:**

        | ML  | Descripcion tipica |
        |-----|--------------------|
        | < 1 | Microsismo, no perceptible |
        | 1-2 | Micro, rara vez perceptible |
        | 2-3 | Menor, perceptible cerca del epicentro |
        | 3-4 | Pequeno, perceptible en un area amplia |
        | 4-5 | Moderado, danos leves posibles |
        | 5-6 | Moderado-fuerte, danos en estructuras debiles |
        | 6-7 | Fuerte, danos significativos |
        | > 7 | Mayor / Gran terremoto |
        """
    )
