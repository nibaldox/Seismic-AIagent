"""Cargador masivo de datos Kelunji/ACE organizados por Estación/Data/Fecha/Hora."""

from __future__ import annotations

import re
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import streamlit as st

from src.streamlit_utils.session_state import (
    get_session,
    register_stream,
    set_current_stream,
    set_histogram_data,
)
from src.streamlit_utils.appearance import handle_error

st.set_page_config(page_title="Batch Loader Kelunji", page_icon="🗂️", layout="wide")

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

# Patrón de fecha en carpetas: DD-MM-YY  (p.ej. 02-05-25)
_DATE_FOLDER_RE = re.compile(r"^(\d{2})-(\d{2})-(\d{2})$")
# Ruta base por defecto: carpeta data/ del proyecto
_DEFAULT_DATA_PATH = str(Path(__file__).resolve().parent.parent / "data")


# ---------------------------------------------------------------------------
# Helpers de escaneo de estructura
# ---------------------------------------------------------------------------

def _parse_date_folder(name: str) -> Optional[date]:
    """Convierte '22-04-25' → date(2025,4,22). Retorna None si no coincide."""
    m = _DATE_FOLDER_RE.match(name)
    if not m:
        return None
    dd, mm, yy = int(m.group(1)), int(m.group(2)), int(m.group(3))
    year = 2000 + yy if yy < 100 else yy
    try:
        return date(year, mm, dd)
    except ValueError:
        return None


def scan_kelunji_structure(root: Path) -> Dict[str, Dict[date, Dict[int, List[Path]]]]:
    """Escanea la estructura Kelunji y retorna un árbol anidado.

    Estructura esperada:
        <root>/
          <Estación>/
            Data/
              <DD-MM-YY>/
                <HH>/
                  *.ms

    Retorna:
        {
            "AC-1-SUR": {
                date(2025,5,2): {
                    0: [Path(...),...],
                    1: [Path(...),...],
                },
            },
            ...
        }
    """
    tree: Dict[str, Dict[date, Dict[int, List[Path]]]] = {}

    if not root.is_dir():
        return tree

    for station_dir in sorted(root.iterdir()):
        if not station_dir.is_dir():
            continue
        data_dir = station_dir / "Data"
        if not data_dir.is_dir():
            # Intentar sin capitalización exacta
            candidates = [d for d in station_dir.iterdir() if d.is_dir() and d.name.lower() == "data"]
            if not candidates:
                continue
            data_dir = candidates[0]

        dates_map: Dict[date, Dict[int, List[Path]]] = {}
        for date_dir in sorted(data_dir.iterdir()):
            if not date_dir.is_dir():
                continue
            d = _parse_date_folder(date_dir.name)
            if d is None:
                continue
            hours_map: Dict[int, List[Path]] = {}
            for hour_dir in sorted(date_dir.iterdir()):
                if not hour_dir.is_dir():
                    continue
                try:
                    h = int(hour_dir.name)
                except ValueError:
                    continue
                ms_files = sorted(hour_dir.glob("*.ms"))
                if ms_files:
                    hours_map[h] = ms_files
            if hours_map:
                dates_map[d] = hours_map
        if dates_map:
            tree[station_dir.name] = dates_map

    return tree


def count_files(tree: Dict, stations: List[str], dates: List[date], hours: List[int]) -> int:
    total = 0
    for st_name in stations:
        for d in dates:
            for h in hours:
                total += len(tree.get(st_name, {}).get(d, {}).get(h, []))
    return total


def collect_files(tree: Dict, stations: List[str], dates: List[date], hours: List[int]) -> List[Path]:
    files: List[Path] = []
    for st_name in stations:
        for d in dates:
            for h in hours:
                files.extend(tree.get(st_name, {}).get(d, {}).get(h, []))
    return files


# ---------------------------------------------------------------------------
# Merge de MiniSEED con progreso
# ---------------------------------------------------------------------------

def merge_mseed_files(
    files: List[Path],
    *,
    decimate_factor: int = 1,
    progress_bar=None,
    status_text=None,
) -> Tuple[Optional[object], str]:
    """Carga y fusiona lista de archivos .ms.

    Retorna (Stream, summary_text) o (None, error_msg).
    """
    try:
        from obspy import Stream, read  # type: ignore
    except ImportError:
        return None, "ObsPy no está instalado."

    st_all = Stream()
    total = len(files)
    errors = 0

    for i, path in enumerate(files):
        if progress_bar is not None:
            progress_bar.progress((i + 1) / total)
        if status_text is not None:
            status_text.caption(f"Cargando {i + 1}/{total}: {path.name}")
        try:
            tr = read(str(path))
            st_all += tr
        except Exception:
            errors += 1
            continue

    if len(st_all) == 0:
        return None, f"No se pudo cargar ningún trace ({errors} errores)."

    # Ordenar antes de merge
    try:
        st_all.sort()
    except Exception:
        pass

    # Merge: method=1 interpola gaps, fill_value=0 rellena con cero
    try:
        st_all.merge(method=1, fill_value=0.0)
    except Exception as exc:
        # Merge suave: solo ordena
        pass

    # Decimación opcional (reduce tasa de muestreo)
    if decimate_factor > 1:
        for tr in st_all:
            try:
                tr.decimate(decimate_factor, strict_length=False)
            except Exception:
                pass

    # Generar resumen
    duration_s = max(
        (tr.stats.npts * tr.stats.delta for tr in st_all if tr.stats.npts > 0),
        default=0.0,
    )
    duration_h = duration_s / 3600.0

    lines = [
        f"BATCH MERGE | {len(files)} archivos .ms | {errors} errores",
        f"Traces resultantes: {len(st_all)}",
        f"Duración máx: {duration_h:.2f} h ({duration_s:.0f} s)",
    ]
    for tr in st_all:
        lines.append(str(tr.stats))

    return st_all, "\n".join(lines)


# ---------------------------------------------------------------------------
# Merge de histogramas CSV
# ---------------------------------------------------------------------------

def merge_histogram_csvs(root: Path, stations: List[str], dates: List[date]):
    """Combina CSVs de histogramas de las estaciones y fechas seleccionadas."""
    import pandas as pd

    frames: List[pd.DataFrame] = []
    files_found: List[str] = []

    for st_name in stations:
        hist_dir = root / st_name / "Histograma"
        if not hist_dir.is_dir():
            # Intentar sin capitalización
            candidates = [d for d in (root / st_name).iterdir() if d.is_dir() and d.name.lower() == "histograma"]
            if not candidates:
                continue
            hist_dir = candidates[0]

        for d in dates:
            csv_path = hist_dir / f"{d.strftime('%Y-%m-%d')}.csv"
            if not csv_path.exists():
                continue
            try:
                df = pd.read_csv(csv_path, comment="#")
                df["_station"] = st_name
                df["_source_file"] = csv_path.name
                # Parsear datetime si existe
                if "datetime" in df.columns:
                    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
                frames.append(df)
                files_found.append(f"{st_name}/{csv_path.name}")
            except Exception:
                continue

    if not frames:
        return None, None, []

    import pandas as pd
    combined = pd.concat(frames, ignore_index=True)
    if "datetime" in combined.columns:
        combined = combined.sort_values("datetime").reset_index(drop=True)

    return combined, {}, files_found


# ---------------------------------------------------------------------------
# Página principal
# ---------------------------------------------------------------------------

def main():
    st.title("🗂️ Batch Loader — Estructura Kelunji/ACE")
    st.caption(
        "Escanea la carpeta de datos del acelerógrafo, selecciona estación, "
        "fechas y rango horario, y genera un dataset fusionado listo para análisis."
    )

    session = get_session()

    # ── Ruta raíz ──────────────────────────────────────────────────────────
    with st.sidebar:
        st.header("Configuración")
        root_path_str = st.text_input(
            "Ruta raíz de datos",
            value=_DEFAULT_DATA_PATH,
            help="Carpeta que contiene las subcarpetas de estaciones (AC-1-SUR, AC-2.1-NORTE, etc.)",
        )
        scan_btn = st.button("🔍 Escanear carpeta", type="primary", use_container_width=True)

    root = Path(root_path_str.strip().strip('"'))

    # Escanear al pulsar botón o si ya hay árbol en sesión
    tree_key = "batch_loader_tree"
    tree_root_key = "batch_loader_root"

    if scan_btn or (st.session_state.get(tree_root_key) != str(root) and root.is_dir()):
        with st.spinner("Escaneando estructura de carpetas..."):
            tree = scan_kelunji_structure(root)
        st.session_state[tree_key] = tree
        st.session_state[tree_root_key] = str(root)
    else:
        tree = st.session_state.get(tree_key, {})

    if not tree:
        if not root.is_dir():
            st.error(f"La ruta no existe o no es una carpeta: `{root}`")
        else:
            st.info("Pulsa **Escanear carpeta** en la barra lateral para detectar estaciones y fechas.")
        return

    # ── Resumen del escaneo ────────────────────────────────────────────────
    all_stations = list(tree.keys())
    all_dates: List[date] = sorted(
        {d for st_dates in tree.values() for d in st_dates.keys()}
    )

    st.success(
        f"Detectadas **{len(all_stations)}** estación(es) · "
        f"**{len(all_dates)}** fecha(s) · "
        f"raíz: `{root}`"
    )

    col_info = st.columns(len(all_stations))
    for i, st_name in enumerate(all_stations):
        total_files = sum(
            len(files)
            for date_map in tree[st_name].values()
            for files in date_map.values()
        )
        with col_info[i]:
            st.metric(st_name, f"{total_files} archivos .ms")

    st.divider()

    # ── Selección de filtros ───────────────────────────────────────────────
    st.subheader("1. Filtros de selección")

    col_f1, col_f2 = st.columns([1, 2])

    with col_f1:
        sel_stations = st.multiselect(
            "Estaciones",
            options=all_stations,
            default=all_stations,
            help="Selecciona una o más estaciones a combinar",
        )

    with col_f2:
        date_labels = [d.strftime("%d/%m/%Y") for d in all_dates]
        sel_date_labels = st.multiselect(
            "Fechas",
            options=date_labels,
            default=date_labels,
            help="Selecciona una o más fechas",
        )
        sel_dates = [all_dates[date_labels.index(lbl)] for lbl in sel_date_labels]

    # Rango horario
    st.markdown("**Rango horario (horas del día)**")
    hour_col1, hour_col2 = st.columns(2)
    with hour_col1:
        hour_start = st.number_input("Desde (hora)", min_value=0, max_value=23, value=0, step=1)
    with hour_col2:
        hour_end = st.number_input("Hasta (hora)", min_value=0, max_value=23, value=23, step=1)

    sel_hours = list(range(int(hour_start), int(hour_end) + 1))

    # Contar archivos seleccionados
    n_files = count_files(tree, sel_stations, sel_dates, sel_hours)

    if n_files == 0:
        st.warning("Sin archivos con la selección actual. Ajusta los filtros.")
    else:
        estimated_mb = n_files * 57 / 1024  # ~57 KB por archivo
        estimated_h = n_files / 60.0  # 1 archivo por minuto aprox.
        st.info(
            f"📦 **{n_files}** archivos seleccionados · "
            f"~{estimated_mb:.0f} MB en disco · "
            f"~{estimated_h:.1f} h de datos"
        )

    st.divider()

    # ── Opciones de carga ──────────────────────────────────────────────────
    st.subheader("2. Opciones de carga")

    col_o1, col_o2, col_o3 = st.columns(3)
    with col_o1:
        load_waveforms = st.checkbox("Cargar waveforms (.ms)", value=True)
    with col_o2:
        load_histograms = st.checkbox("Cargar histogramas (.csv)", value=True)
    with col_o3:
        decimate_factor = st.selectbox(
            "Decimación",
            options=[1, 2, 4, 8, 10],
            index=0,
            help="Factor de decimación (reduce tasa de muestreo). 1 = sin decimación.",
        )

    if decimate_factor > 1:
        st.caption(
            f"⚡ Decimación ×{decimate_factor}: reduce datos a 1/{decimate_factor} "
            "para análisis rápido. Puede perder detalle de alta frecuencia."
        )

    dataset_name_input = st.text_input(
        "Nombre del dataset fusionado",
        value=f"BATCH_{'+'.join(sel_stations)}_{datetime.now().strftime('%Y%m%d_%H%M')}",
        help="Nombre que aparecerá en el selector de datasets de las otras páginas.",
    )

    # ── Botón de carga ─────────────────────────────────────────────────────
    st.divider()
    st.subheader("3. Ejecutar carga")

    load_disabled = n_files == 0 or (not load_waveforms and not load_histograms)
    load_btn = st.button(
        f"🚀 Cargar y fusionar {n_files} archivos",
        type="primary",
        disabled=load_disabled,
        use_container_width=True,
    )

    if load_btn:
        results_container = st.container()

        # ── Waveforms ──────────────────────────────────────────────────────
        if load_waveforms and n_files > 0:
            st.markdown("#### Cargando waveforms...")
            progress_bar = st.progress(0.0)
            status_text = st.empty()

            files_to_load = collect_files(tree, sel_stations, sel_dates, sel_hours)

            merged_stream, summary_or_err = merge_mseed_files(
                files_to_load,
                decimate_factor=int(decimate_factor),
                progress_bar=progress_bar,
                status_text=status_text,
            )

            progress_bar.empty()
            status_text.empty()

            if merged_stream is None:
                st.error(f"Error al fusionar waveforms: {summary_or_err}")
            else:
                dataset_name = dataset_name_input.strip() or f"BATCH_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                register_stream(stream=merged_stream, name=dataset_name, summary=summary_or_err)
                set_current_stream(dataset_name, session=session)

                n_traces = len(merged_stream)
                with results_container:
                    st.success(
                        f"✅ Dataset **{dataset_name}** creado con "
                        f"**{n_traces}** traces a partir de {len(files_to_load)} archivos. "
                        "Puedes navegar al **Waveform Viewer** ahora."
                    )
                    with st.expander("Ver resumen del stream", expanded=False):
                        st.code(summary_or_err, language="text")

        # ── Histogramas ────────────────────────────────────────────────────
        if load_histograms and sel_dates and sel_stations:
            st.markdown("#### Cargando histogramas...")
            with st.spinner("Combinando CSVs de histogramas..."):
                df_hist, meta_hist, files_hist = merge_histogram_csvs(root, sel_stations, sel_dates)

            if df_hist is None:
                st.warning("No se encontraron CSVs de histogramas para la selección indicada.")
            else:
                hist_filename = f"HIST_{'+'.join(sel_stations)}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
                set_histogram_data(df=df_hist, meta=meta_hist or {}, filename=hist_filename)

                with results_container:
                    st.success(
                        f"✅ Histogramas combinados: **{df_hist.shape[0]}** filas · "
                        f"**{df_hist.shape[1]}** columnas · "
                        f"fuentes: {', '.join(files_hist)}"
                    )
                    with st.expander("Vista previa histogramas", expanded=False):
                        st.dataframe(df_hist.head(30), use_container_width=True)

        if not load_disabled:
            st.info(
                "💡 Ve a **Waveform Viewer** o **Spectrum Analysis** para analizar "
                "el dataset fusionado, o a **Series Temporales Gecko** para los histogramas."
            )

    # ── Estado actual de la sesión ─────────────────────────────────────────
    from src.streamlit_utils.session_state import list_dataset_names, get_current_stream_name
    dataset_names = list_dataset_names(session=session)
    if dataset_names:
        st.divider()
        st.subheader("Datasets cargados en sesión")
        current = get_current_stream_name(session=session)
        for name in dataset_names:
            badge = "🟢 activo" if name == current else "⚪"
            st.markdown(f"- {badge} `{name}`")


main()
