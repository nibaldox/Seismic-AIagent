"""Dashboard de monitoreo continuo — SeismoAnalyzer Pro.

Muestra series temporales de PGA, PGV y temperatura/telemetría desde
los datos de histograma cargados en sesión, con umbrales de alerta configurables.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv

from src.streamlit_utils.session_state import (
    get_session,
    get_histogram_data,
    get_current_stream,
    get_current_stream_name,
)
from src.core.intensity_measures import compute_all_ims

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=False)

st.set_page_config(
    page_title="Monitor de Alertas",
    page_icon="📡",
    layout="wide",
)

st.title("📡 Monitor de Alertas")
st.caption(
    "Visualiza la evolución temporal de PGA, PGV y telemetría del equipo. "
    "Configura umbrales para identificar eventos que superan límites de diseño."
)

session = get_session()

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR — configuración de umbrales
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Umbrales de alerta")

    st.subheader("Aceleración (PGA)")
    pga_warn = st.number_input(
        "Alerta PGA (cm/s²)",
        min_value=0.1, max_value=2000.0, value=50.0, step=5.0,
        key="mon_pga_warn",
        help="PGA amarillo — evento moderado",
    )
    pga_crit = st.number_input(
        "Crítico PGA (cm/s²)",
        min_value=0.1, max_value=2000.0, value=200.0, step=10.0,
        key="mon_pga_crit",
        help="PGA rojo — evento severo",
    )

    st.subheader("Velocidad (PGV)")
    pgv_warn = st.number_input(
        "Alerta PGV (cm/s)",
        min_value=0.01, max_value=500.0, value=5.0, step=0.5,
        key="mon_pgv_warn",
    )
    pgv_crit = st.number_input(
        "Crítico PGV (cm/s)",
        min_value=0.01, max_value=500.0, value=30.0, step=1.0,
        key="mon_pgv_crit",
    )

    st.divider()
    st.subheader("Telemetría")
    temp_warn = st.number_input(
        "Alerta Temperatura (°C)",
        min_value=0.0, max_value=100.0, value=50.0, step=1.0,
        key="mon_temp_warn",
    )
    temp_crit = st.number_input(
        "Crítico Temperatura (°C)",
        min_value=0.0, max_value=100.0, value=65.0, step=1.0,
        key="mon_temp_crit",
    )

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _threshold_band(fig: go.Figure, warn: float, crit: float, axis: str = "y") -> None:
    """Añade líneas horizontales de umbral en amarillo y rojo."""
    fig.add_hline(
        y=warn, line=dict(color="orange", dash="dash", width=1.5),
        annotation_text="⚠ Alerta", annotation_position="top right",
    )
    fig.add_hline(
        y=crit, line=dict(color="red", dash="dash", width=1.5),
        annotation_text="🚨 Crítico", annotation_position="top right",
    )


def _color_series(values: np.ndarray, warn: float, crit: float) -> list[str]:
    """Devuelve colores por valor para scatter markers."""
    colors = []
    for v in values:
        if v >= crit:
            colors.append("#ff4444")
        elif v >= warn:
            colors.append("#ffaa00")
        else:
            colors.append("#55efc4")
    return colors


def _summary_kpis(values: np.ndarray, warn: float, crit: float, unit: str) -> None:
    """Muestra KPIs de resumen en 4 columnas."""
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Máximo", f"{np.max(values):.2f} {unit}")
    c2.metric("Mediana", f"{np.median(values):.2f} {unit}")
    n_warn = int(np.sum(values >= warn))
    n_crit = int(np.sum(values >= crit))
    c3.metric("Eventos ≥ alerta", str(n_warn), delta=None)
    c4.metric(
        "Eventos ≥ crítico",
        str(n_crit),
        delta=None,
        delta_color="off",
    )
    if n_crit > 0:
        st.error(f"🚨 {n_crit} registros superan el umbral **crítico** ({crit:.1f} {unit})")
    elif n_warn > 0:
        st.warning(f"⚠️ {n_warn} registros superan el umbral de **alerta** ({warn:.1f} {unit})")
    else:
        st.success(f"✅ Todos los registros están por debajo del umbral de alerta.")


# ─────────────────────────────────────────────────────────────────────────────
# PESTAÑA 1 — PGA/PGV calculados desde el dataset activo
# ─────────────────────────────────────────────────────────────────────────────
tab_seismic, tab_tele, tab_log = st.tabs([
    "🌍 Acelerogramas (PGA / PGV)",
    "🌡️ Telemetría Gecko",
    "📋 Log de Alertas",
])

with tab_seismic:
    stream = get_current_stream(session)
    ds_name = get_current_stream_name(session)

    if stream is None:
        st.info(
            "No hay dataset activo. Carga datos desde **Uploader** (pág. 00) "
            "o **Batch Loader** (pág. 01)."
        )
    else:
        st.subheader(f"Dataset: `{ds_name}`")
        traces = list(stream)

        # Calcular IMs por traza
        rows = []
        with st.spinner("Calculando IMs por traza…"):
            for tr in traces:
                try:
                    ims = compute_all_ims(tr)
                    t_start = tr.stats.starttime.datetime if tr.stats.starttime else None
                    rows.append({
                        "traza": str(tr.id),
                        "t_start": t_start,
                        "PGA_cms2": ims.pga_cms2 if ims.pga_cms2 is not None else np.nan,
                        "PGV_cms": ims.pgv_cms if ims.pgv_cms is not None else np.nan,
                        "PGD_cm": ims.pgd_cm if ims.pgd_cm is not None else np.nan,
                        "Arias_ms": ims.arias_intensity_ms if ims.arias_intensity_ms is not None else np.nan,
                        "Dur_D5_75_s": ims.duration_5_75_s if ims.duration_5_75_s is not None else np.nan,
                    })
                except Exception:
                    pass

        if not rows:
            st.warning("No se pudieron calcular IMs para las trazas del dataset.")
        else:
            df_ims = pd.DataFrame(rows).dropna(subset=["PGA_cms2"])
            df_ims = df_ims.sort_values("t_start").reset_index(drop=True)
            x_axis = df_ims["t_start"] if df_ims["t_start"].notna().any() else df_ims.index
            x_label = "Fecha/hora inicio" if df_ims["t_start"].notna().any() else "Índice de traza"

            # ── PGA ──
            st.subheader("Pico de Aceleración (PGA)")
            _summary_kpis(df_ims["PGA_cms2"].values, pga_warn, pga_crit, "cm/s²")

            fig_pga = go.Figure()
            colors_pga = _color_series(df_ims["PGA_cms2"].values, pga_warn, pga_crit)
            fig_pga.add_trace(go.Scatter(
                x=x_axis, y=df_ims["PGA_cms2"],
                mode="lines+markers",
                name="PGA",
                line=dict(color="#74b9ff", width=1.5),
                marker=dict(color=colors_pga, size=7),
                hovertemplate="%{x}<br>PGA: %{y:.2f} cm/s²<extra></extra>",
            ))
            _threshold_band(fig_pga, pga_warn, pga_crit)
            fig_pga.update_layout(
                template="plotly_dark",
                xaxis_title=x_label,
                yaxis_title="PGA (cm/s²)",
                height=320,
                margin=dict(t=20, b=40),
                hovermode="x unified",
            )
            st.plotly_chart(fig_pga, use_container_width=True)

            # ── PGV ──
            st.subheader("Pico de Velocidad (PGV)")
            pgv_valid = df_ims["PGV_cms"].dropna()
            if len(pgv_valid) > 0:
                _summary_kpis(df_ims["PGV_cms"].values, pgv_warn, pgv_crit, "cm/s")
                fig_pgv = go.Figure()
                colors_pgv = _color_series(df_ims["PGV_cms"].fillna(0).values, pgv_warn, pgv_crit)
                fig_pgv.add_trace(go.Scatter(
                    x=x_axis, y=df_ims["PGV_cms"],
                    mode="lines+markers",
                    name="PGV",
                    line=dict(color="#a29bfe", width=1.5),
                    marker=dict(color=colors_pgv, size=7),
                    hovertemplate="%{x}<br>PGV: %{y:.3f} cm/s<extra></extra>",
                ))
                _threshold_band(fig_pgv, pgv_warn, pgv_crit)
                fig_pgv.update_layout(
                    template="plotly_dark",
                    xaxis_title=x_label,
                    yaxis_title="PGV (cm/s)",
                    height=280,
                    margin=dict(t=20, b=40),
                    hovermode="x unified",
                )
                st.plotly_chart(fig_pgv, use_container_width=True)
            else:
                st.info("PGV no disponible (requiere integración — tasas de muestreo muy bajas pueden dar NaN).")

            # ── Arias Intensity ──
            with st.expander("Intensidad de Arias y Duración Significativa", expanded=False):
                col_a, col_b = st.columns(2)
                with col_a:
                    fig_ai = go.Figure()
                    fig_ai.add_trace(go.Bar(
                        x=df_ims["traza"], y=df_ims["Arias_ms"],
                        name="I_A",
                        marker_color="#fdcb6e",
                        hovertemplate="%{x}<br>I_A: %{y:.4f} m/s<extra></extra>",
                    ))
                    fig_ai.update_layout(
                        template="plotly_dark",
                        title="Intensidad de Arias (m/s)",
                        xaxis_title="Traza",
                        yaxis_title="I_A (m/s)",
                        height=280,
                        margin=dict(t=40, b=60),
                    )
                    st.plotly_chart(fig_ai, use_container_width=True)
                with col_b:
                    fig_dur = go.Figure()
                    fig_dur.add_trace(go.Bar(
                        x=df_ims["traza"], y=df_ims["Dur_D5_75_s"],
                        name="D5-75",
                        marker_color="#00cec9",
                        hovertemplate="%{x}<br>D5-75: %{y:.1f} s<extra></extra>",
                    ))
                    fig_dur.update_layout(
                        template="plotly_dark",
                        title="Duración significativa D5-75 (s)",
                        xaxis_title="Traza",
                        yaxis_title="D5-75 (s)",
                        height=280,
                        margin=dict(t=40, b=60),
                    )
                    st.plotly_chart(fig_dur, use_container_width=True)

            # ── Tabla completa ──
            with st.expander("Tabla de IMs completa", expanded=False):
                st.dataframe(df_ims.set_index("traza"), use_container_width=True)
                try:
                    import io as _io
                    buf = _io.BytesIO()
                    df_ims.to_excel(buf, index=False, sheet_name="Monitor_IMs")
                    st.download_button(
                        "⬇️ Exportar tabla a Excel",
                        data=buf.getvalue(),
                        file_name=f"monitor_ims_{ds_name or 'dataset'}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="dl_monitor_ims",
                    )
                except ImportError:
                    st.caption("Instala `openpyxl` para exportar a Excel.")


# ─────────────────────────────────────────────────────────────────────────────
# PESTAÑA 2 — Telemetría Gecko (histogramas de temperatura, voltaje, etc.)
# ─────────────────────────────────────────────────────────────────────────────
with tab_tele:
    df_hist, meta_hist, filename_hist = get_histogram_data(session)

    if df_hist is None:
        st.info(
            "No hay datos de telemetría cargados. "
            "Ve a **Histogramas Gecko** (pág. 04) para cargar un CSV/Excel."
        )
    else:
        st.subheader(f"Telemetría: `{filename_hist or 'sesión'}`")
        if meta_hist:
            with st.expander("Metadatos del archivo", expanded=False):
                st.json(meta_hist)

        # Columnas numéricas disponibles
        num_cols = [c for c in df_hist.columns if pd.api.types.is_numeric_dtype(df_hist[c])]
        dt_col = "datetime" if "datetime" in df_hist.columns else None

        if not num_cols:
            st.warning("No se encontraron columnas numéricas en los datos de telemetría.")
        else:
            # Detectar columna de tiempo para eje X
            if dt_col:
                try:
                    df_hist[dt_col] = pd.to_datetime(df_hist[dt_col], errors="coerce")
                except Exception:
                    dt_col = None
            x_tele = df_hist[dt_col] if dt_col else df_hist.index

            # Selector de columnas a visualizar
            default_cols = [c for c in num_cols if any(
                kw in c.lower() for kw in ["temp", "volt", "bat", "pga", "pgv", "accel"]
            )] or num_cols[:3]
            selected_cols = st.multiselect(
                "Variables a monitorear",
                options=num_cols,
                default=default_cols,
                key="mon_tele_cols",
            )

            if not selected_cols:
                st.info("Selecciona al menos una variable.")
            else:
                # Detectar si hay columna de temperatura
                temp_cols = [c for c in selected_cols if "temp" in c.lower()]

                for col in selected_cols:
                    vals = df_hist[col].dropna().values
                    if len(vals) == 0:
                        continue

                    st.subheader(f"📊 {col}")

                    # KPIs
                    k1, k2, k3 = st.columns(3)
                    k1.metric("Máximo", f"{np.max(vals):.3g}")
                    k2.metric("Mínimo", f"{np.min(vals):.3g}")
                    k3.metric("Promedio", f"{np.mean(vals):.3g}")

                    # Gráfico
                    is_temp = col in temp_cols
                    w_val = temp_warn if is_temp else None
                    c_val = temp_crit if is_temp else None

                    colors_tele = (
                        _color_series(df_hist[col].fillna(0).values, w_val, c_val)
                        if is_temp else "#74b9ff"
                    )

                    fig_tele = go.Figure()
                    fig_tele.add_trace(go.Scatter(
                        x=x_tele,
                        y=df_hist[col],
                        mode="lines+markers",
                        name=col,
                        line=dict(color="#74b9ff", width=1.5),
                        marker=dict(color=colors_tele, size=4) if is_temp else dict(size=4),
                        hovertemplate=f"%{{x}}<br>{col}: %{{y:.3g}}<extra></extra>",
                    ))

                    if is_temp and w_val is not None:
                        _threshold_band(fig_tele, w_val, c_val)
                        # Alertas de temperatura
                        n_warn_t = int(np.sum(df_hist[col].fillna(0) >= w_val))
                        n_crit_t = int(np.sum(df_hist[col].fillna(0) >= c_val))
                        if n_crit_t > 0:
                            st.error(f"🚨 {n_crit_t} registros de temperatura ≥ {c_val}°C")
                        elif n_warn_t > 0:
                            st.warning(f"⚠️ {n_warn_t} registros de temperatura ≥ {w_val}°C")

                    fig_tele.update_layout(
                        template="plotly_dark",
                        xaxis_title="Tiempo",
                        yaxis_title=col,
                        height=260,
                        margin=dict(t=10, b=40),
                        hovermode="x unified",
                    )
                    st.plotly_chart(fig_tele, use_container_width=True)

                # Estadísticas por período
                if dt_col and pd.api.types.is_datetime64_any_dtype(df_hist[dt_col]):
                    with st.expander("📅 Estadísticas por período", expanded=False):
                        period = st.radio(
                            "Agrupar por",
                            ["Día", "Semana", "Mes"],
                            horizontal=True,
                            key="mon_tele_period",
                        )
                        freq_map = {"Día": "D", "Semana": "W", "Mes": "ME"}
                        freq = freq_map[period]
                        try:
                            df_grp = (
                                df_hist.set_index(dt_col)[selected_cols]
                                .resample(freq)
                                .agg(["mean", "max", "min", "std"])
                            )
                            df_grp.columns = [f"{c}_{s}" for c, s in df_grp.columns]
                            st.dataframe(df_grp, use_container_width=True)
                        except Exception as exc:
                            st.caption(f"Error al agrupar: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# PESTAÑA 3 — Log de alertas exportable
# ─────────────────────────────────────────────────────────────────────────────
with tab_log:
    import io as _io_log

    st.subheader("📋 Log de eventos que superan umbrales")
    st.caption(
        "Consolida todos los registros (acelerogramas y telemetría) que superan "
        "los umbrales configurados en el panel lateral. Exportable a CSV/Excel."
    )

    log_rows: list[dict] = []
    now_str = pd.Timestamp.utcnow().isoformat(timespec="seconds") + "Z"

    # ── Eventos sísmicos (PGA / PGV) ─────────────────────────────────────
    stream_log = get_current_stream(session)
    if stream_log is not None:
        for tr in list(stream_log):
            try:
                ims = compute_all_ims(tr)
                t_start = tr.stats.starttime.datetime if tr.stats.starttime else None
                pga = ims.pga_cms2
                pgv = ims.pgv_cms

                level_pga = (
                    "CRÍTICO" if pga is not None and pga >= pga_crit
                    else "ALERTA" if pga is not None and pga >= pga_warn
                    else None
                )
                level_pgv = (
                    "CRÍTICO" if pgv is not None and pgv >= pgv_crit
                    else "ALERTA" if pgv is not None and pgv >= pgv_warn
                    else None
                )

                if level_pga:
                    log_rows.append({
                        "timestamp_utc": t_start,
                        "fuente": "Acelerograma",
                        "variable": "PGA",
                        "traza": str(tr.id),
                        "valor": round(pga, 3),
                        "unidad": "cm/s²",
                        "umbral_alerta": pga_warn,
                        "umbral_critico": pga_crit,
                        "nivel": level_pga,
                        "generado": now_str,
                    })
                if level_pgv:
                    log_rows.append({
                        "timestamp_utc": t_start,
                        "fuente": "Acelerograma",
                        "variable": "PGV",
                        "traza": str(tr.id),
                        "valor": round(pgv, 4),
                        "unidad": "cm/s",
                        "umbral_alerta": pgv_warn,
                        "umbral_critico": pgv_crit,
                        "nivel": level_pgv,
                        "generado": now_str,
                    })
            except Exception:
                pass

    # ── Eventos de telemetría ─────────────────────────────────────────────
    df_h, _, fname_h = get_histogram_data(session)
    if df_h is not None:
        dt_col_log = "datetime" if "datetime" in df_h.columns else None
        temp_cols_log = [c for c in df_h.columns if "temp" in c.lower()
                         and pd.api.types.is_numeric_dtype(df_h[c])]

        for col in temp_cols_log:
            vals = df_h[col].fillna(np.nan)
            for idx_row, val in vals.items():
                if np.isnan(val):
                    continue
                level = (
                    "CRÍTICO" if val >= temp_crit
                    else "ALERTA" if val >= temp_warn
                    else None
                )
                if level:
                    ts = df_h[dt_col_log].iloc[idx_row] if dt_col_log else None
                    log_rows.append({
                        "timestamp_utc": ts,
                        "fuente": f"Telemetría ({fname_h or 'CSV'})",
                        "variable": col,
                        "traza": "—",
                        "valor": round(float(val), 3),
                        "unidad": "°C",
                        "umbral_alerta": temp_warn,
                        "umbral_critico": temp_crit,
                        "nivel": level,
                        "generado": now_str,
                    })

    if not log_rows:
        st.success(
            "✅ Sin eventos de alerta con los umbrales actuales. "
            "Ajusta los umbrales en el panel lateral si esperas ver eventos."
        )
    else:
        df_log = pd.DataFrame(log_rows).sort_values("nivel", key=lambda s: s.map({"CRÍTICO": 0, "ALERTA": 1}))
        n_crit_log = int((df_log["nivel"] == "CRÍTICO").sum())
        n_warn_log = int((df_log["nivel"] == "ALERTA").sum())

        lc1, lc2 = st.columns(2)
        lc1.metric("Eventos críticos 🚨", str(n_crit_log))
        lc2.metric("Eventos de alerta ⚠️", str(n_warn_log))

        # Colorear filas por nivel
        def _row_color(row: pd.Series) -> list[str]:
            bg = "background-color: #5f1010" if row["nivel"] == "CRÍTICO" else "background-color: #4a3a00"
            return [bg] * len(row)

        try:
            st.dataframe(
                df_log.style.apply(_row_color, axis=1),
                use_container_width=True,
                height=min(600, 50 + 35 * len(df_log)),
            )
        except Exception:
            st.dataframe(df_log, use_container_width=True)

        # Exportar CSV
        csv_log = _io_log.StringIO()
        df_log.to_csv(csv_log, index=False)
        col_exp1, col_exp2 = st.columns(2)
        col_exp1.download_button(
            "⬇️ Exportar log CSV",
            data=csv_log.getvalue(),
            file_name=f"alert_log_{pd.Timestamp.utcnow().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            key="dl_alert_csv",
        )

        # Exportar Excel
        try:
            buf_log = _io_log.BytesIO()
            df_log.to_excel(buf_log, index=False, sheet_name="AlertLog")
            col_exp2.download_button(
                "⬇️ Exportar log Excel",
                data=buf_log.getvalue(),
                file_name=f"alert_log_{pd.Timestamp.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="dl_alert_xlsx",
            )
        except ImportError:
            col_exp2.caption("Instala `openpyxl` para exportar a Excel.")
