import io
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict, List

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
from src.ai_agent.seismic_interpreter import load_agent_suite, run_histogram_analysis
from src.streamlit_utils.appearance import handle_error
from src.streamlit_utils.session_state import get_session, set_team_telemetry_context, set_histogram_data, get_histogram_data, clear_histogram_data

# Load environment variables
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=False)

st.set_page_config(page_title="Histogramas Gecko", page_icon="📈")


def _get_agent_suite():
    if "ai_agents" in st.session_state:
        return st.session_state["ai_agents"]
    try:
        agents = load_agent_suite()
        st.session_state["ai_agents"] = agents
        st.session_state.pop("ai_agents_error", None)
        return agents
    except Exception as exc:
        st.session_state["ai_agents_error"] = str(exc)
        st.session_state["ai_agents"] = {}
        return {}


def _render_histogram_ai_panel(*, container, key_prefix: str, filename: str | None, meta: Dict[str, str] | None, df_head_md: str, columns: List[str], time_range: str | None, notes_builder):
    session = get_session()
    agents = _get_agent_suite()
    agent_error = st.session_state.get("ai_agents_error")
    if not agents:
        if agent_error:
            container.error(f"No se pudo inicializar el interprete: {agent_error}")
        else:
            container.info("Configura los agentes IA en config/agno_config.yaml.")
        return
    if not df_head_md.strip():
        container.info("Selecciona datos validos para enviar al interprete.")
        return
    context_signature = f"{filename or 'session'}|{key_prefix}"
    context_key = f"{key_prefix}_context"
    done_key = f"{key_prefix}_auto_done"
    result_key = f"{key_prefix}_result"
    if st.session_state.get(context_key) != context_signature:
        st.session_state[context_key] = context_signature
        st.session_state[done_key] = False
        st.session_state.pop(result_key, None)
        session.ai_results.pop(f"{key_prefix}_analysis", None)
    run_requested = False
    if not st.session_state.get(done_key, False):
        run_requested = True
    if container.button("Actualizar analisis IA", key=f"{key_prefix}_run"):
        run_requested = True
        st.session_state[done_key] = False
    if run_requested:
        notes = notes_builder() if notes_builder else None
        try:
            with st.spinner("Consultando interprete..."):
                content = run_histogram_analysis(
                    agents,
                    filename=filename,
                    meta=meta,
                    df_head=df_head_md,
                    columns=columns,
                    time_range=time_range,
                    notes=notes,
                )
        except Exception as exc:
            handle_error(exc, context="Error al ejecutar el agente de histogramas")
            content = None
        if content:
            st.session_state[result_key] = content
            session.ai_results[f"{key_prefix}_analysis"] = content
        else:
            st.session_state[result_key] = None
        st.session_state[done_key] = True
    result = st.session_state.get(result_key) or session.ai_results.get(f"{key_prefix}_analysis")
    if result:
        container.markdown(result)
    else:
        container.info("El interprete IA aun no tiene resultados.")


def _find_histogram_files(base: Path) -> list[Path]:
    patterns = [
        "**/Histograma/**/*.csv",
        "**/Histograma/**/*.txt",
        "**/histograma/**/*.csv",
        "**/histograma/**/*.txt",
    ]
    files: list[Path] = []
    for pat in patterns:
        files.extend(base.glob(pat))
    # De-duplicate and sort
    uniq = sorted({f.resolve() for f in files if f.is_file()})
    return uniq


def _parse_gecko_metadata(file_bytes: bytes) -> Dict[str, str]:
    meta: Dict[str, str] = {}
    try:
        text = file_bytes.decode("utf-8", errors="ignore")
    except Exception:
        return meta
    for line in text.splitlines():
        if not line.startswith("#"):
            break
        # Strip leading '# ' and split on first '='
        body = line.lstrip("#").strip()
        if not body or "=" not in body:
            continue
        key, val = body.split("=", 1)
        key = key.strip().strip('"')
        val = val.strip().strip('"')
        meta[key] = val
    return meta


def _read_table_with_meta(file_bytes: bytes, filename: str) -> Tuple[pd.DataFrame, Dict[str, str]]:
    name_lower = filename.lower()
    meta = _parse_gecko_metadata(file_bytes)
    buf = io.BytesIO(file_bytes)
    if name_lower.endswith(".xlsx"):
        return pd.read_excel(buf), meta
    # Try flexible CSV parsing, skipping '#' metadata lines
    try:
        return pd.read_csv(buf, sep=None, engine="python", comment="#"), meta
    except Exception:
        buf.seek(0)
        # Fallback: comma
        try:
            return pd.read_csv(buf, comment="#"), meta
        except Exception:
            buf.seek(0)
            # Fallback: semicolon
            return pd.read_csv(buf, sep=";", comment="#"), meta


def _ensure_datetime(df: pd.DataFrame) -> pd.DataFrame:
    """Parse a 'datetime' column to pandas datetime if present."""
    if "datetime" in df.columns:
        try:
            df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
        except Exception:
            pass
    return df


def _detect_histogram_columns(df: pd.DataFrame) -> Tuple[Optional[str], Optional[str]]:
    cols = [c for c in df.columns]
    lower = {c: str(c).strip().lower() for c in cols}
    # Common names
    bin_candidates = [
        c for c in cols if lower[c] in {"bin", "bins", "value", "val", "amplitude", "x"}
    ]
    count_candidates = [
        c for c in cols if lower[c] in {"count", "counts", "n", "freq", "frequency", "y"}
    ]
    # If both found, return first pair
    if bin_candidates and count_candidates:
        return bin_candidates[0], count_candidates[0]
    # If exactly two numeric columns, assume first is bin and second is count
    num_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
    if len(num_cols) == 2:
        return num_cols[0], num_cols[1]
    return None, None


def _plot_aggregated_histogram(df: pd.DataFrame, bin_col: str, count_col: str, *, logy: bool, normalize: bool, cumulative: bool) -> go.Figure:
    x = df[bin_col].to_numpy()
    y = df[count_col].to_numpy(dtype=float)
    if normalize and y.sum() > 0:
        y = y / y.sum()
    if cumulative:
        y = np.cumsum(y)
        if normalize and y[-1] != 0:
            y = y / y[-1]
    fig = go.Figure(
        data=[go.Bar(x=x, y=y, marker_color="#74b9ff")]
    )
    fig.update_layout(
        template="plotly_dark",
        xaxis_title=str(bin_col),
        yaxis_title=("Prob." if normalize else ("Cuentas" if not cumulative else "Cumul.")),
        bargap=0.05,
        hovermode="x unified",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=40, r=20, b=60, l=70),
    )
    fig.update_yaxes(type="log" if logy else "linear")
    return fig


def _plot_raw_histogram(series: pd.Series, *, bins: int, logy: bool, normalize: bool, cumulative: bool) -> go.Figure:
    data = series.dropna().to_numpy()
    counts, edges = np.histogram(data, bins=bins)
    if normalize and counts.sum() > 0:
        counts = counts / counts.sum()
    if cumulative:
        counts = np.cumsum(counts)
        if normalize and counts[-1] != 0:
            counts = counts / counts[-1]
    centers = (edges[:-1] + edges[1:]) / 2.0
    fig = go.Figure(data=[go.Bar(x=centers, y=counts, marker_color="#55efc4")])
    fig.update_layout(
        template="plotly_dark",
        xaxis_title=series.name or "valor",
        yaxis_title=("Prob." if normalize else ("Cuentas" if not cumulative else "Cumul.")),
        bargap=0.05,
        hovermode="x unified",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=40, r=20, b=60, l=70),
    )
    fig.update_yaxes(type="log" if logy else "linear")
    return fig


def main():
    st.title("📈 Histogramas Gecko")
    st.caption("Carga un archivo de histograma exportado por Gecko o construye un histograma desde datos crudos.")

    # Intentar recuperar datos del estado de sesión
    df, meta, filename = get_histogram_data()
    
    with st.sidebar:
        st.header("Fuente de datos")
        
        # Mostrar información de datos cargados si existen
        if df is not None and filename:
            st.success(f"📊 Datos cargados: {filename}")
            st.caption(f"{df.shape[0]} filas, {df.shape[1]} columnas")
            if st.button("🗑️ Limpiar datos", help="Eliminar los datos actuales de la sesión"):
                clear_histogram_data()
                st.rerun()
            st.divider()
        
        mode = st.radio("Modo", ["Subir archivo", "Buscar en data/"], disabled=(df is not None))

    # Si no hay datos en sesión, permitir carga
    if df is None:
        if mode == "Subir archivo":
            up = st.file_uploader("Archivo (.csv/.txt/.xlsx)", type=["csv", "txt", "xlsx"], accept_multiple_files=False)
            if up is not None:
                try:
                    file_bytes = up.read()
                    df, meta = _read_table_with_meta(file_bytes, up.name)
                    df = _ensure_datetime(df)
                    filename = up.name
                    # Guardar en estado de sesión
                    set_histogram_data(df=df, meta=meta, filename=filename)
                except Exception as e:
                    st.error(f"No se pudo leer el archivo: {e}")
                    return
        else:
            base = Path("data").resolve()
            files = _find_histogram_files(base)
            if not files:
                st.warning("No se encontraron archivos en data/**/Histograma/**.")
            else:
                options = [str(f.relative_to(base)) for f in files]
                sel = st.selectbox("Selecciona archivo", options=options)
                if sel:
                    p = base / sel
                    try:
                        file_bytes = p.read_bytes()
                        df, meta = _read_table_with_meta(file_bytes, p.name)
                        df = _ensure_datetime(df)
                        filename = p.name
                        # Guardar en estado de sesión
                        set_histogram_data(df=df, meta=meta, filename=filename)
                    except Exception as e:
                        st.error(f"No se pudo leer {p}: {e}")
                        return

    if df is None:
        st.info("Selecciona o sube un archivo para continuar.")
        return

    st.success(f"Cargado: {filename} | {df.shape[0]} filas, {df.shape[1]} columnas")
    with st.expander("Vista previa"):
        st.dataframe(df.head(50))
    if meta:
        with st.expander("Metadatos Gecko"):
            left, right = st.columns(2)
            for i, (k, v) in enumerate(meta.items()):
                (left if i % 2 == 0 else right).write(f"**{k}:** {v}")

    st.subheader("Visualización")
    viz_mode = st.radio("Modo de gráfico", ["Serie temporal (X = fecha)", "Histograma"])


    if viz_mode == "Serie temporal (X = fecha)":
        if "datetime" not in df.columns:
            st.error("No se encontro columna 'datetime' en el archivo para usar como eje X.")
            st.stop()
        num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        if not num_cols:
            st.error("No hay columnas numericas para graficar.")
            st.stop()

        ctrl_left, ctrl_right = st.columns(2)
        with ctrl_left:
            resample = st.selectbox(
                "Resampleo",
                options=["Sin resampleo", "15Min", "1H", "6H", "1D"],
                index=0,
                help="Agrega los datos por ventana de tiempo",
            )
        with ctrl_right:
            agg = st.selectbox("Agregacion", options=["mean", "max", "min"], index=1)

        smooth = st.checkbox("Suavizar (rolling)", value=False)
        if smooth:
            win = st.slider("Ventana rolling (muestras)", min_value=3, max_value=301, value=21, step=2)
        else:
            win = None

        defaults = ["3D peak", "Max_E g", "Max_N g", "Max_Z g"]
        picks: List[str] = []
        for idx in range(4):
            default_col = defaults[idx] if idx < len(defaults) and defaults[idx] in num_cols else num_cols[0]
            picks.append(
                st.selectbox(
                    f"Variable grafico {idx + 1}",
                    options=num_cols,
                    index=num_cols.index(default_col),
                    key=f"ts_var_{idx + 1}",
                )
            )

        def _compute_xy(dataframe: pd.DataFrame, column: str) -> tuple[np.ndarray, np.ndarray]:
            dft = dataframe.dropna(subset=["datetime"]).copy()
            if resample != "Sin resampleo":
                dft = dft.set_index("datetime")
                try:
                    series = getattr(dft[column].resample(resample), agg)()
                except Exception:
                    series = dft[column].resample("1H").mean()
                if smooth and win:
                    series = series.rolling(window=win, min_periods=max(3, win // 5), center=True).mean()
                return np.asarray(series.index.to_pydatetime()), series.values.astype(float)
            series = dft[["datetime", column]].dropna()
            yvals = series[column].astype(float)
            if smooth and win:
                yvals = yvals.rolling(window=win, min_periods=max(3, win // 5), center=True).mean()
            return series["datetime"].to_numpy(), yvals.to_numpy()

        colors = ["#74b9ff", "#ff7675", "#55efc4", "#ffa726"]
        xmins, xmaxs = [], []
        xy_cache: Dict[str, tuple[np.ndarray, np.ndarray]] = {}

        col_plot, col_ai = st.columns([3, 2])
        with col_plot:
            for idx, column in enumerate(picks, start=1):
                xarr, yarr = _compute_xy(df, column)
                xy_cache[column] = (xarr, yarr)
                if len(xarr) > 0:
                    xmins.append(xarr[0])
                    xmaxs.append(xarr[-1])
                fig = go.Figure(
                    data=[
                        go.Scatter(
                            x=xarr,
                            y=yarr,
                            mode="lines",
                            name=column,
                            line=dict(color=colors[(idx - 1) % len(colors)], width=2),
                        )
                    ]
                )
                fig.update_layout(
                    template="plotly_dark",
                    xaxis_title="Fecha",
                    yaxis_title=column,
                    hovermode="x unified",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    margin=dict(t=30, r=20, b=40, l=70),
                    showlegend=False,
                )
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        subcols = [c for c in picks if c in df.columns]
        df_small = df[["datetime"] + subcols].dropna().head(20) if "datetime" in df.columns else df[subcols].dropna().head(20)
        try:
            df_head_md = df_small.to_markdown(index=False)
        except Exception:
            df_head_md = df_small.to_string(index=False)

        time_span = None
        if xmins and xmaxs:
            try:
                time_span = f"{min(xmins)} -> {max(xmaxs)}"
            except Exception:
                time_span = None

        def notes_builder():
            analysis_ts = datetime.now().isoformat(timespec="seconds")
            stat_lines = []
            for column in subcols:
                try:
                    _, y = xy_cache.get(column, (np.array([]), np.array([])))
                    y = y[np.isfinite(y)] if y is not None else np.array([])
                    if y.size > 0:
                        last_val = y[~np.isnan(y)][-1] if np.any(~np.isnan(y)) else y[-1]
                        stat_lines.append(
                            f"{column}: n={y.size}, min={np.nanmin(y):.3g}, mean={np.nanmean(y):.3g}, max={np.nanmax(y):.3g}, last={last_val:.3g}"
                        )
                except Exception:
                    continue
            stats_block = " | ".join(stat_lines)
            base = f"resample={resample}; agg={agg}; smooth={'on' if smooth else 'off'}"
            if smooth and win:
                base += f" (win={win})"
            base += f"; analysis_ts={analysis_ts}"
            if stats_block:
                base += f"; stats: {stats_block}"
            return base

        with col_ai:
            col_ai.subheader("Interprete IA")
            _render_histogram_ai_panel(
                container=col_ai,
                key_prefix="hist_ts",
                filename=filename,
                meta=meta,
                df_head_md=df_head_md,
                columns=subcols,
                time_range=time_span,
                notes_builder=notes_builder,
            )
            try:
                export_notes = f"resample={resample}; agg={agg}; smooth={'on' if smooth else 'off'}" + (f" (win={win})" if smooth and win else "")
                set_team_telemetry_context(
                    time_range=time_span,
                    columns=subcols,
                    df_head_md=df_head_md,
                    notes=export_notes,
                    meta=meta,
                    filename=filename,
                )
                col_ai.caption("Contexto enviado a 'AI Equipo IA'.")
            except Exception:
                pass
        return

    # --- Histograma ---
    st.subheader("Configuración de histograma")
    logy = st.checkbox("Escala log en Y", value=False)
    normalize = st.checkbox("Normalizar (probabilidad)", value=False)
    cumulative = st.checkbox("Acumulado", value=False)

    bin_col, count_col = _detect_histogram_columns(df)
    aggregated = False
    if bin_col is not None and count_col is not None:
        aggregated = st.toggle(
            "Interpretar como histograma ya agregado (bin + count)",
            value=True,
            help=f"Detectado: bin='{bin_col}', count='{count_col}'"
        )
    else:
        st.caption("No se detectaron columnas 'bin' y 'count'. Se construirá desde una columna numérica.")


    if aggregated:
        cols = list(df.columns)
        bin_col = st.selectbox("Columna bin", options=cols, index=cols.index(bin_col) if bin_col in cols else 0)
        count_col = st.selectbox("Columna count", options=cols, index=cols.index(count_col) if count_col in cols else 1)
        fig = _plot_aggregated_histogram(df, bin_col, count_col, logy=logy, normalize=normalize, cumulative=cumulative)
        col_plot, col_ai = st.columns([3, 2])
        with col_plot:
            col_plot.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        df_small = df[[bin_col, count_col]].dropna().head(20)
        try:
            df_head_md = df_small.to_markdown(index=False)
        except Exception:
            df_head_md = df_small.to_string(index=False)
        time_span = None
        if "datetime" in df.columns:
            try:
                dt_clean = pd.to_datetime(df["datetime"], errors="coerce")
                dt_min = dt_clean.min(); dt_max = dt_clean.max()
                if pd.notna(dt_min) and pd.notna(dt_max):
                    time_span = f"{dt_min} -> {dt_max}"
            except Exception:
                pass

        def agg_notes():
            analysis_ts = datetime.now().isoformat(timespec="seconds")
            try:
                total = float(pd.to_numeric(df[count_col], errors="coerce").fillna(0).sum())
                idx_max = int(pd.to_numeric(df[count_col], errors="coerce").fillna(0).idxmax())
                top_bin = df.loc[idx_max, bin_col] if 0 <= idx_max < len(df) else None
                top_cnt = df.loc[idx_max, count_col] if 0 <= idx_max < len(df) else None
                x = pd.to_numeric(df[bin_col], errors="coerce").fillna(0).to_numpy()
                y = pd.to_numeric(df[count_col], errors="coerce").fillna(0).to_numpy()
                w_mean = float((x * y).sum() / y.sum()) if y.sum() > 0 else None
                stats = f"total={total:.3g}; top=({top_bin},{top_cnt})"
                if w_mean is not None:
                    stats += f"; w_mean={w_mean:.3g}"
            except Exception:
                stats = ""
            base = (
                f"histograma agregado; normalize={normalize}; cumulative={cumulative}; logy={logy}; analysis_ts={analysis_ts}"
            )
            if stats:
                base += f"; {stats}"
            return base

        with col_ai:
            col_ai.subheader("Interprete IA")
            _render_histogram_ai_panel(
                container=col_ai,
                key_prefix="hist_agg",
                filename=filename,
                meta=meta,
                df_head_md=df_head_md,
                columns=[bin_col, count_col],
                time_range=time_span,
                notes_builder=agg_notes,
            )
        return

    else:
        num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        if not num_cols:
            st.error("No hay columnas numericas para construir histograma.")
            return
        preferred = [
            "3D peak",
            "Max_E g",
            "Max_N g",
            "Max_Z g",
            "Voltage",
            "Temperature",
        ]
        default_idx = 0
        for name in preferred:
            if name in num_cols:
                default_idx = num_cols.index(name)
                break
        value_col = st.selectbox("Columna de valores", options=num_cols, index=default_idx)
        bins = st.slider("Bins", min_value=5, max_value=200, value=50, step=1)
        fig = _plot_raw_histogram(df[value_col], bins=bins, logy=logy, normalize=normalize, cumulative=cumulative)
        col_plot, col_ai = st.columns([3, 2])
        with col_plot:
            col_plot.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        df_small = df[["datetime", value_col]].dropna().head(20) if "datetime" in df.columns else df[[value_col]].dropna().head(20)
        try:
            df_head_md = df_small.to_markdown(index=False)
        except Exception:
            df_head_md = df_small.to_string(index=False)
        time_span = None
        if "datetime" in df.columns:
            try:
                dt_clean = pd.to_datetime(df["datetime"], errors="coerce")
                dt_min = dt_clean.min(); dt_max = dt_clean.max()
                if pd.notna(dt_min) and pd.notna(dt_max):
                    time_span = f"{dt_min} -> {dt_max}"
            except Exception:
                pass

        def column_notes():
            analysis_ts = datetime.now().isoformat(timespec="seconds")
            try:
                series = pd.to_numeric(df[value_col], errors="coerce").dropna()
                n = int(series.size)
                if n:
                    stats = f"n={n}; min={series.min():.3g}; median={series.median():.3g}; mean={series.mean():.3g}; max={series.max():.3g}"
                else:
                    stats = ""
            except Exception:
                stats = ""
            base = f"histograma desde columna='{value_col}'; bins={bins}; normalize={normalize}; cumulative={cumulative}; logy={logy}; analysis_ts={analysis_ts}"
            if stats:
                base += f"; {stats}"
            return base

        with col_ai:
            col_ai.subheader("Interprete IA")
            _render_histogram_ai_panel(
                container=col_ai,
                key_prefix="hist_raw",
                filename=filename,
                meta=meta,
                df_head_md=df_head_md,
                columns=[value_col],
                time_range=time_span,
                notes_builder=column_notes,
            )
        return



if __name__ == "__main__":
    main()
