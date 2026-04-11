"""Reporte final integrado — SeismoAnalyzer Pro.

Genera automáticamente un informe completo con todos los resultados
disponibles en la sesión activa: waveforms, IMs, espectros, HVSR,
RotD50, picks P/S e interpretación IA.
También produce un archivo HTML autocontenido descargable.
"""
from __future__ import annotations

import datetime
import io
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

from src.streamlit_utils.session_state import (
    get_current_stream,
    get_current_stream_name,
    get_histogram_data,
    get_pipeline_steps,
    get_session,
    list_dataset_names,
    list_picks,
    list_trace_labels,
    set_current_stream,
    get_qc_results,
)
from src.core.intensity_measures import compute_all_ims
from src.visualization.waveform_plots import create_waveform_plot
from src.visualization.spectrum_plots import create_fft_plot, create_psd_plot

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=False)

st.set_page_config(
    page_title="Reporte Final",
    page_icon="📄",
    layout="wide",
)

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _pipeline_badge(step: str, done_steps: set[str]) -> str:
    ok = step in done_steps
    color = "#55efc4" if ok else "#636e72"
    icon  = "✅" if ok else "⬜"
    return f"<span style='color:{color};font-weight:bold'>{icon} {step}</span>"


def _fig_to_html(fig: go.Figure, height: int = 350) -> str:
    """Devuelve el HTML embebible de un gráfico Plotly (sin include_plotlyjs)."""
    return fig.to_html(full_html=False, include_plotlyjs=False, default_height=height)


def _ims_dataframe(stream) -> pd.DataFrame:
    rows = []
    for tr in stream:
        try:
            ims = compute_all_ims(tr)
            row = {"Traza": str(tr.id)}
            row.update({k: (round(v, 4) if v is not None else None)
                        for k, v in ims.to_dict().items()})
            rows.append(row)
        except Exception:
            pass
    return pd.DataFrame(rows).set_index("Traza") if rows else pd.DataFrame()


def _build_html_report(
    ds_name: str,
    generated_at: str,
    pipeline_html: str,
    kpi_html: str,
    df_ims: pd.DataFrame,
    fig_waveform: go.Figure | None,
    fig_fft: go.Figure | None,
    fig_psd: go.Figure | None,
    response_spec_data: dict | None,
    hvsr_result: Any | None,
    rotd_result: Any | None,
    picks: list,
    ai_results: dict,
    df_hist: pd.DataFrame | None,
    *,
    cosmos_mode: bool = False,
    cover_page: dict | None = None,
) -> str:
    """Genera el HTML completo del informe."""

    sections: list[str] = []

    # ── Portada COSMOS ────────────────────────────────────────────────────
    if cosmos_mode and cover_page:
        cp = cover_page
        sections.append(f"""<div class="cosmos-cover">
<h1>COSMOS Earthquake Analysis Report</h1>
<table class="cover-table">
<tr><th>Número de informe</th><td>{cp.get('report_number', '—')}</td></tr>
<tr><th>Nombre del proyecto</th><td>{cp.get('project_name', '—')}</td></tr>
<tr><th>Nombre del sitio / estación</th><td>{cp.get('site_name', ds_name)}</td></tr>
<tr><th>Descripción del evento</th><td>{cp.get('event_desc', '—')}</td></tr>
<tr><th>Analista responsable</th><td>{cp.get('analyst', '—')}</td></tr>
<tr><th>Fecha del informe</th><td>{cp.get('report_date', generated_at)}</td></tr>
<tr><th>Latitud</th><td>{cp.get('latitude', '—')}</td></tr>
<tr><th>Longitud</th><td>{cp.get('longitude', '—')}</td></tr>
</table>
</div>""")

    # ── Waveforms ──────────────────────────────────────────────────────────
    if fig_waveform:
        sections.append(f"""
<h2>Waveforms</h2>
{_fig_to_html(fig_waveform, height=320)}
""")

    # ── IMs ───────────────────────────────────────────────────────────────
    if not df_ims.empty:
        sections.append(f"""
<h2>Parámetros de Intensidad Sísmica (IMs)</h2>
{df_ims.to_html(classes='ims-table', border=0)}
""")

    # ── FFT / PSD ─────────────────────────────────────────────────────────
    if fig_fft:
        sections.append(f"<h2>Espectro de Amplitud (FFT)</h2>{_fig_to_html(fig_fft, 300)}")
    if fig_psd:
        sections.append(f"<h2>Densidad Espectral de Potencia (PSD)</h2>{_fig_to_html(fig_psd, 300)}")

    # ── Espectro de respuesta vs código ───────────────────────────────────
    if response_spec_data:
        fig_rs = go.Figure()
        fig_rs.add_trace(go.Scatter(
            x=response_spec_data["periods_rec"], y=response_spec_data["sa_rec"],
            mode="lines", name="Registro",
            line=dict(color="#74b9ff", width=2),
        ))
        fig_rs.add_trace(go.Scatter(
            x=response_spec_data["periods_code"], y=response_spec_data["sa_code"],
            mode="lines", name=response_spec_data["code_label"],
            line=dict(color="#ff7675", width=2, dash="dash"),
        ))
        fig_rs.update_layout(
            template="plotly_dark",
            xaxis=dict(type="log", title="T (s)"),
            yaxis_title="Sa (cm/s²)",
            title="Espectro de Respuesta vs. Código de Diseño",
            height=320, margin=dict(t=40, b=40),
        )
        sections.append(f"<h2>Espectro de Respuesta vs. Código de Diseño</h2>{_fig_to_html(fig_rs, 320)}")

    # ── RotD50 ────────────────────────────────────────────────────────────
    if rotd_result is not None:
        fig_rd = go.Figure()
        fig_rd.add_trace(go.Scatter(
            x=rotd_result.periods, y=rotd_result.rotd50,
            mode="lines", name="RotD50", line=dict(color="#74b9ff", width=2),
        ))
        fig_rd.add_trace(go.Scatter(
            x=rotd_result.periods, y=rotd_result.rotd100,
            mode="lines", name="RotD100", line=dict(color="#fd79a8", width=1.5, dash="dot"),
        ))
        fig_rd.update_layout(
            template="plotly_dark",
            xaxis=dict(type="log", title="T (s)"),
            yaxis_title="Sa (cm/s²)",
            title=f"RotD50/RotD100 — {rotd_result.comp1_id} · {rotd_result.comp2_id}",
            height=300, margin=dict(t=40, b=40),
        )
        sections.append(f"<h2>Espectro RotD50 / RotD100 (PEER)</h2>{_fig_to_html(fig_rd, 300)}")

    # ── HVSR ──────────────────────────────────────────────────────────────
    if hvsr_result is not None:
        fig_hv = go.Figure()
        fig_hv.add_trace(go.Scatter(
            x=hvsr_result.freqs, y=hvsr_result.hv_plus1,
            mode="lines", line=dict(width=0), showlegend=False,
        ))
        fig_hv.add_trace(go.Scatter(
            x=hvsr_result.freqs, y=hvsr_result.hv_minus1,
            mode="lines", line=dict(width=0),
            fill="tonexty", fillcolor="rgba(116,185,255,0.15)", name="±1σ",
        ))
        fig_hv.add_trace(go.Scatter(
            x=hvsr_result.freqs, y=hvsr_result.hv_mean,
            mode="lines", name="H/V media", line=dict(color="#74b9ff", width=2.5),
        ))
        fig_hv.add_vline(x=hvsr_result.f0_hz,
            line=dict(color="#fdcb6e", dash="dash"),
            annotation_text=f"f₀={hvsr_result.f0_hz:.2f} Hz")
        fig_hv.update_layout(
            template="plotly_dark",
            xaxis=dict(type="log", title="Frecuencia (Hz)"),
            yaxis_title="H/V",
            title=f"HVSR — f₀={hvsr_result.f0_hz:.2f} Hz · T₀={hvsr_result.t0_s:.2f} s",
            height=300, margin=dict(t=40, b=40),
        )
        sesame_html = hvsr_result.sesame.summary.replace("\n", "<br>")
        sections.append(f"""
<h2>HVSR — Caracterización de Sitio (SESAME)</h2>
{_fig_to_html(fig_hv, 300)}
<pre style='background:#2d3436;color:#dfe6e9;padding:12px;border-radius:6px;'>{sesame_html}</pre>
""")

    # ── Picks P/S ─────────────────────────────────────────────────────────
    if picks:
        df_picks = pd.DataFrame(picks)
        sections.append(f"<h2>Picks P/S</h2>{df_picks.to_html(classes='ims-table', border=0, index=False)}")

    # ── Telemetría ────────────────────────────────────────────────────────
    if df_hist is not None and not df_hist.empty:
        sections.append(f"""
<h2>Telemetría (primeras 20 filas)</h2>
{df_hist.head(20).to_html(classes='ims-table', border=0, index=False)}
""")

    # ── Interpretación IA ─────────────────────────────────────────────────
    for key, content in ai_results.items():
        if content:
            label = key.replace("_", " ").title()
            sections.append(f"<h2>Interpretación IA — {label}</h2><div class='ai-text'>{content}</div>")

    body = "\n".join(sections) if sections else "<p>Sin datos disponibles en esta sesión.</p>"

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Informe Sísmico — {ds_name}</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background:#1e272e; color:#dfe6e9;
         max-width:1200px; margin:0 auto; padding:24px; }}
  h1   {{ color:#74b9ff; border-bottom:2px solid #74b9ff; padding-bottom:8px; }}
  h2   {{ color:#a29bfe; margin-top:40px; }}
  .meta {{ color:#b2bec3; font-size:0.9em; margin-bottom:24px; }}
  .kpi-grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(180px,1fr));
               gap:16px; margin:20px 0; }}
  .kpi {{ background:#2d3436; border-radius:8px; padding:16px; text-align:center; }}
  .kpi .val {{ font-size:1.8em; font-weight:bold; color:#55efc4; }}
  .kpi .lbl {{ font-size:0.82em; color:#b2bec3; margin-top:4px; }}
  .pipeline {{ display:flex; gap:16px; flex-wrap:wrap; margin:16px 0; }}
  .ims-table {{ border-collapse:collapse; width:100%; margin:12px 0; font-size:0.85em; }}
  .ims-table th {{ background:#2d3436; padding:8px 12px; text-align:left; color:#74b9ff; }}
  .ims-table td {{ padding:6px 12px; border-bottom:1px solid #2d3436; }}
  .ims-table tr:hover td {{ background:#2d3436; }}
  .ai-text {{ background:#2d3436; padding:16px; border-radius:8px;
              line-height:1.6; white-space:pre-wrap; font-size:0.9em; }}
  pre {{ overflow-x:auto; }}
  .cosmos-cover {{ background:#2d3436; border-radius:10px; padding:24px; margin-bottom:32px; border-left:4px solid #74b9ff; }}
  .cosmos-cover h1 {{ color:#74b9ff; font-size:1.4em; margin-bottom:16px; border-bottom:1px solid #74b9ff; padding-bottom:8px; }}
  .cover-table {{ width:100%; border-collapse:collapse; font-size:0.9em; }}
  .cover-table th {{ text-align:left; color:#a29bfe; padding:4px 12px; width:220px; }}
  .cover-table td {{ color:#dfe6e9; padding:4px 12px; }}
  h1.cosmos-doc {{ color:#74b9ff; font-size:1.6em; }}
</style>
</head>
<body>
<h1 class="{'cosmos-doc' if cosmos_mode else ''}">📄 {'Informe COSMOS —' if cosmos_mode else 'Informe Sísmico —'} {ds_name}</h1>
<div class="meta">Generado: {generated_at} | SeismoAnalyzer Pro{' · Formato COSMOS V1→V3' if cosmos_mode else ''}</div>

<h2>Estado del pipeline</h2>
<div class="pipeline">{pipeline_html}</div>

<h2>Indicadores clave</h2>
<div class="kpi-grid">{kpi_html}</div>

{body}

<hr style="border-color:#2d3436;margin-top:60px">
<p style="color:#636e72;font-size:0.8em;text-align:center">
  Generado con SeismoAnalyzer Pro · {generated_at}
</p>
</body>
</html>"""


# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

st.title("📄 Reporte Final Integrado")
st.caption("Consolida automáticamente todos los resultados de la sesión en un informe interactivo y descargable.")

session = get_session()
stream  = get_current_stream(session)
ds_name = get_current_stream_name(session) or "Sin dataset"

# ── Modo de informe ────────────────────────────────────────────────────────
report_mode = st.radio(
    "Modo de informe",
    options=["simple", "cosmos"],
    format_func=lambda x: {
        "simple": "📋 Simple — resumen rápido",
        "cosmos": "🏛️ COSMOS — estructura formal de 12 secciones",
    }[x],
    horizontal=True,
    index=0,
    help="COSMOS V1→V3 sigue la estructura formal de 12 secciones del estándar COSMOS/PEER para reportes de movimiento fuerte.",
)

# ── Portada COSMOS (editable) ──────────────────────────────────────────────
if report_mode == "cosmos":
    with st.expander("📌 Portada del Informe — Editar antes de exportar", expanded=True):
        st.caption("Estos campos se incluyen en la primera sección del informe COSMOS.")
        cp_col1, cp_col2 = st.columns(2)
        report_number = cp_col1.text_input("Número de informe", value="", placeholder="ej. INF-CSN-2026-001")
        project_name = cp_col1.text_input("Nombre del proyecto", value="", placeholder="ej. Monitoreo Sísmico Central Chile")
        site_name = cp_col2.text_input("Nombre del sitio / estación", value=ds_name, placeholder="ej. Station CSN LLO")
        analyst = cp_col2.text_input("Analista responsable", value="", placeholder="ej. Nombre Apellido")
        event_desc = st.text_input("Descripción del evento", value="", placeholder="ej. Terremoto Mw 6.2, zona de subducción centro-norte de Chile")
        col_date, col_lat, col_lon = st.columns([1, 1, 1])
        report_date_val = col_date.date_input("Fecha del informe", value=datetime.date.today())
        latitude = col_lat.text_input("Latitud (°)", value="", placeholder="-24.17")
        longitude = col_lon.text_input("Longitud (°)", value="", placeholder="-69.04")

if stream is None:
    st.warning("No hay dataset activo. Carga datos desde **Uploader** o **Batch Loader** y ejecuta los análisis antes de generar el reporte.")
    st.stop()

# Limitar el número de trazas en el reporte para evitar MessageSizeError.
# Los datasets batch con muchas horas de datos pueden tener cientos de trazas.
_MAX_REPORT_TRACES = 12
traces_all = list(stream)
if len(traces_all) > _MAX_REPORT_TRACES:
    st.info(
        f"El dataset tiene {len(traces_all)} trazas. "
        f"El reporte muestra las primeras {_MAX_REPORT_TRACES} para evitar límites de tamaño. "
        "Los IMs se calculan para todas."
    )
traces     = traces_all[:_MAX_REPORT_TRACES]
picks      = list_picks(session=session)
done_steps = set(get_pipeline_steps(session=session))
if ds_name:
    done_steps.add("V0_loaded")

df_hist, meta_hist, fname_hist = get_histogram_data(session)

generated_at = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

# ── Barra de estado del pipeline ──────────────────────────────────────────
_STAGES = [
    ("V0", "Datos cargados",     "V0_loaded"),
    ("V1", "Filtrado/Baseline",  "V1_filtered"),
    ("V2", "IMs calculados",     "V2_ims"),
    ("V3", "Espectros/código",   "V3_spectra"),
]
pipe_cols = st.columns(len(_STAGES))
for col, (lbl, desc, key) in zip(pipe_cols, _STAGES):
    done = key in done_steps
    col.metric(
        label=f"{'✅' if done else '⬜'} {lbl}",
        value=desc,
        delta="Completado" if done else "Pendiente",
        delta_color="normal" if done else "off",
    )

st.divider()

# ── Calcular IMs ──────────────────────────────────────────────────────────
with st.spinner("Calculando IMs…"):
    df_ims = _ims_dataframe(stream)

# ── KPIs rápidos ─────────────────────────────────────────────────────────
st.subheader("📊 Indicadores clave")
if not df_ims.empty:
    kpi_cols = st.columns(5)
    def _kpi(col, label, value, unit=""):
        col.metric(label, f"{value} {unit}".strip() if value is not None else "—")

    pga_col  = "pga_cms2" if "pga_cms2" in df_ims.columns else None
    pgv_col  = "pgv_cms"  if "pgv_cms"  in df_ims.columns else None
    arias_col = "arias_intensity_ms" if "arias_intensity_ms" in df_ims.columns else None
    dur_col  = "duration_5_75_s" if "duration_5_75_s" in df_ims.columns else None

    _kpi(kpi_cols[0], "Trazas", len(traces))
    _kpi(kpi_cols[1], "PGA máx (cm/s²)",
         round(df_ims[pga_col].dropna().max(), 2) if pga_col else None)
    _kpi(kpi_cols[2], "PGV máx (cm/s)",
         round(df_ims[pgv_col].dropna().max(), 3) if pgv_col else None)
    _kpi(kpi_cols[3], "I_A máx (m/s)",
         round(df_ims[arias_col].dropna().max(), 4) if arias_col else None)
    _kpi(kpi_cols[4], "D5-75 máx (s)",
         round(df_ims[dur_col].dropna().max(), 1) if dur_col else None)

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# SECCIONES DEL REPORTE
# ─────────────────────────────────────────────────────────────────────────────
trace_labels = list_trace_labels(session=session, stream=traces)
first_trace  = traces[0] if traces else None

# ── Sección 2 COSMOS: Control de Calidad ─────────────────────────────────
if report_mode == "cosmos":
    st.subheader("🔍 Sección 2 — Control de Calidad (QC V0→V1)")
    qc_saved = get_qc_results(ds_name, session=session)
    if qc_saved:
        _VC = {"ACEPTADO": "🟢", "CONDICIONADO": "🟡", "RECHAZADO": "🔴"}
        rows_qc = []
        for lbl, qc in qc_saved.items():
            rows_qc.append({
                "Traza": lbl,
                "Veredicto": f"{_VC.get(qc.get('verdict',''), '⚪')} {qc.get('verdict', '?')}",
                "SNR (dB)": f"{qc.get('snr_db', 0):.1f}",
                "Sat %": f"{qc.get('clip_ratio', 0)*100:.2f}",
                "Gaps": str(qc.get("n_gaps", 0)),
                "Drift %": f"{qc.get('drift_pct', 0):.1f}",
                "Duración (s)": f"{qc.get('duration_s', 0):.1f}",
            })
        st.dataframe(pd.DataFrame(rows_qc).set_index("Traza"), use_container_width=True)
        with st.expander("Veredicto e impacto por traza", expanded=False):
            for lbl, qc in qc_saved.items():
                verdict = qc.get("verdict", "?")
                reasons = qc.get("reasons", [])
                emoji = _VC.get(verdict, "⚪")
                st.markdown(f"**{emoji} {lbl} — {verdict}**")
                if reasons:
                    for r in reasons:
                        st.caption(f"  - {r}")
                else:
                    st.caption("  Sin observaciones.")
    else:
        st.info("No hay resultados QC disponibles. Ejecuta el Control de Calidad en la página **Waveform Viewer** (pág. 02) antes de generar el reporte.")

# ── 1. Waveforms ─────────────────────────────────────────────────────────
st.subheader("🌊 Waveforms" + (" *(Sección 3 — Raw Data)*" if report_mode == "cosmos" else ""))
try:
    fig_waveform = create_waveform_plot(
        traces, (0, int(max((tr.stats.npts * tr.stats.delta for tr in traces), default=300))),
        unit="Raw", picks=picks,
        filter_type="none", freqmin=1.0, freqmax=10.0,
    )
    st.plotly_chart(fig_waveform, use_container_width=True)
except Exception as exc:
    st.warning(f"No se pudo generar el plot de waveforms: {exc}")
    fig_waveform = None

# ── Sección 5 COSMOS: Picks P/S y Localización ────────────────────────────
if report_mode == "cosmos":
    st.subheader("📍 Sección 5 — Picks de Fase y Localización Hipocentral")
    if picks:
        st.dataframe(pd.DataFrame(picks), use_container_width=True)
        # Intentar localización 1D si hay picks P y S
        from src.core.location.one_d_location import locate_event_1d, Station as _S, PSObservation as _PS, OneDVelocityModel as _VM
        p_picks = [pk for pk in picks if pk.get("phase") == "P"]
        s_picks = [pk for pk in picks if pk.get("phase") == "S"]
        if len(p_picks) >= 1 and len(s_picks) >= 1:
            try:
                # Modelo de velocidad genérico para Chile central (Vp=6.0 km/s, Vp/Vs=1.78)
                vel_model = _VM(vp_km_s=6.0, vs_km_s=3.37, name="Chile central genérico")
                stations = [_S(code=pk["station"], latitude=float(meta.get("lat", -24.0)),
                               longitude=float(meta.get("lon", -69.0)), elevation_m=0.0)
                            for pk in picks
                            for meta in [session.metadata or {}]]
                if not stations:
                    stations = [_S(code=pk["station"], latitude=-24.0, longitude=-69.0, elevation_m=0.0)
                                for pk in picks]
                obs = [
                    _PS(station=stations[i], p_time_s=pk["time_rel"], s_time_s=sk["time_rel"])
                    for i, (pk, sk) in enumerate(zip(p_picks, s_picks)) if i < len(stations)
                ]
                if obs:
                    result_loc = locate_event_1d(obs, vel_model)
                    if result_loc:
                        col_loc = st.columns(4)
                        col_loc[0].metric("Latitud", f"{result_loc.latitude:.4f}°")
                        col_loc[1].metric("Longitud", f"{result_loc.longitude:.4f}°")
                        col_loc[2].metric("Profundidad", f"{result_loc.depth_km:.1f} km")
                        col_loc[3].metric("Error (km)", f"{result_loc.rms:.2f}")
                        if hasattr(result_loc, "magnitude") and result_loc.magnitude:
                            st.caption(f"Magnitud estimada: Mw {result_loc.magnitude:.1f}")
            except Exception as exc:
                st.caption(f"Localización no disponible: {exc}")
        else:
            st.caption(f" Picks insuficientes para localización: {len(p_picks)} P + {len(s_picks)} S (mínimo 1P + 1S).")
    else:
        st.info("Sin picks registrados.")

# ── 2. Tabla de IMs ──────────────────────────────────────────────────────
st.subheader("📐 Parámetros de Intensidad Sísmica (IMs)" + (" *(Sección 7)*" if report_mode == "cosmos" else ""))
if not df_ims.empty:
    st.dataframe(df_ims, use_container_width=True)
else:
    st.info("No se pudieron calcular IMs.")

# ── 3. Espectro FFT + PSD (primera traza) ────────────────────────────────
fig_fft, fig_psd = None, None
if first_trace is not None:
    st.subheader("📈 Análisis Espectral — Primera traza" + (" *(Sección 8 — FAS / PSD)*" if report_mode == "cosmos" else ""))
    col_fft, col_psd = st.columns(2)
    try:
        fig_fft = create_fft_plot(first_trace)
        col_fft.plotly_chart(fig_fft, use_container_width=True)
    except Exception as exc:
        col_fft.warning(f"FFT: {exc}")
    try:
        fig_psd = create_psd_plot(first_trace)
        col_psd.plotly_chart(fig_psd, use_container_width=True)
    except Exception as exc:
        col_psd.warning(f"PSD: {exc}")

# ── 4. Espectro de respuesta vs código ───────────────────────────────────
response_spec_data = st.session_state.get("response_spec_data")
if response_spec_data:
    st.subheader("📐 Espectro de Respuesta vs. Código de Diseño" + (" *(Sección 9)*" if report_mode == "cosmos" else ""))
    fig_rs = go.Figure()
    fig_rs.add_trace(go.Scatter(
        x=response_spec_data["periods_rec"], y=response_spec_data["sa_rec"],
        mode="lines", name="Registro", line=dict(color="#74b9ff", width=2),
    ))
    fig_rs.add_trace(go.Scatter(
        x=response_spec_data["periods_code"], y=response_spec_data["sa_code"],
        mode="lines", name=response_spec_data["code_label"],
        line=dict(color="#ff7675", width=2, dash="dash"),
    ))
    fig_rs.update_layout(
        template="plotly_dark",
        xaxis=dict(type="log", title="T (s)"),
        yaxis_title="Sa (cm/s²)",
        title="Espectro de Respuesta vs. Código de Diseño",
        height=350, margin=dict(t=40, b=40), hovermode="x unified",
    )
    st.plotly_chart(fig_rs, use_container_width=True)

# ── 5. RotD50 ─────────────────────────────────────────────────────────────
rotd_result = st.session_state.get("rotd_result")
if rotd_result is not None:
    st.subheader("🔄 Espectro RotD50 / RotD100" + (" *(Sección 10 — RotD50/RotD100 PEER)*" if report_mode == "cosmos" else ""))
    fig_rd = go.Figure()
    fig_rd.add_trace(go.Scatter(
        x=rotd_result.periods, y=rotd_result.rotd50,
        mode="lines", name="RotD50", line=dict(color="#74b9ff", width=2),
    ))
    fig_rd.add_trace(go.Scatter(
        x=rotd_result.periods, y=rotd_result.rotd100,
        mode="lines", name="RotD100", line=dict(color="#fd79a8", width=1.5, dash="dot"),
    ))
    fig_rd.update_layout(
        template="plotly_dark",
        xaxis=dict(type="log", title="T (s)"),
        yaxis_title="Sa (cm/s²)",
        title=f"RotD50/RotD100 · ξ={rotd_result.damping*100:.0f}%",
        height=320, margin=dict(t=40, b=40), hovermode="x unified",
        legend=dict(x=0.01, y=0.99),
    )
    st.plotly_chart(fig_rd, use_container_width=True)

# ── 6. HVSR ───────────────────────────────────────────────────────────────
hvsr_result = st.session_state.get("hvsr_result")
if hvsr_result is not None:
    st.subheader("🌊 HVSR — Caracterización de Sitio" + (" *(Sección 11 — Nakamura HVSR / SESAME)*" if report_mode == "cosmos" else ""))
    fig_hv = go.Figure()
    fig_hv.add_trace(go.Scatter(
        x=hvsr_result.freqs, y=hvsr_result.hv_plus1,
        mode="lines", line=dict(width=0), showlegend=False,
    ))
    fig_hv.add_trace(go.Scatter(
        x=hvsr_result.freqs, y=hvsr_result.hv_minus1,
        mode="lines", line=dict(width=0),
        fill="tonexty", fillcolor="rgba(116,185,255,0.15)", name="±1σ",
    ))
    fig_hv.add_trace(go.Scatter(
        x=hvsr_result.freqs, y=hvsr_result.hv_mean,
        mode="lines", name="H/V media", line=dict(color="#74b9ff", width=2.5),
    ))
    fig_hv.add_vline(x=hvsr_result.f0_hz,
        line=dict(color="#fdcb6e", dash="dash"),
        annotation_text=f"f₀={hvsr_result.f0_hz:.2f} Hz",
        annotation_position="top right")
    fig_hv.add_hline(y=2.0, line=dict(color="orange", dash="dot", width=1))
    fig_hv.update_layout(
        template="plotly_dark",
        xaxis=dict(type="log", title="Frecuencia (Hz)"),
        yaxis_title="H/V",
        title=f"HVSR · f₀={hvsr_result.f0_hz:.2f} Hz · T₀={hvsr_result.t0_s:.2f} s",
        height=340, margin=dict(t=50, b=40), hovermode="x unified",
    )
    col_hv, col_se = st.columns([3, 1])
    col_hv.plotly_chart(fig_hv, use_container_width=True)
    with col_se:
        st.subheader("Criterios SESAME")
        s = hvsr_result.sesame
        for passed, label, detail in [
            (s.c1_passed, "C1 — Ciclos", s.c1_detail),
            (s.c2_passed, "C2 — σ/A",    s.c2_detail),
            (s.c3_passed, "C3 — Pico",   s.c3_detail),
        ]:
            icon = "✅" if passed else "❌"
            st.markdown(f"**{icon} {label}**")
            st.caption(detail)
        overall = "✅ VÁLIDA" if s.all_passed else "⚠️ DUDOSA"
        st.metric("Resultado", overall)

# ── 7. Picks P/S (modo simple) ───────────────────────────────────────────
if report_mode != "cosmos" and picks:
    st.subheader("📍 Picks P/S")
    st.dataframe(pd.DataFrame(picks), use_container_width=True)

# ── 8. Telemetría (modo simple) ────────────────────────────────────────────
if report_mode != "cosmos" and df_hist is not None and not df_hist.empty:
    st.subheader("🌡️ Telemetría Gecko")
    st.caption(f"Fuente: {fname_hist or 'sesión'} · {df_hist.shape[0]} filas")
    num_cols_h = [c for c in df_hist.columns if pd.api.types.is_numeric_dtype(df_hist[c])][:6]
    st.dataframe(df_hist[num_cols_h].describe().T.round(3), use_container_width=True)

# ── 9. Interpretación IA ─────────────────────────────────────────────────
ai_results = {k: v for k, v in session.ai_results.items() if v}
if ai_results:
    st.subheader("🤖 Interpretación IA" + (" *(Sección 12 — Conclusiones y Recomendaciones)*" if report_mode == "cosmos" else ""))
    for key, content in ai_results.items():
        label = key.replace("_", " ").title()
        with st.expander(f"🔍 {label}", expanded=True):
            st.markdown(content)

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# GENERACIÓN DEL INFORME HTML
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("⬇️ Exportar Informe")

# Pipeline HTML para el informe
_STAGE_KEYS = [("V0", "Datos cargados", "V0_loaded"),
               ("V1", "Filtrado/Baseline", "V1_filtered"),
               ("V2", "IMs calculados", "V2_ims"),
               ("V3", "Espectros/código", "V3_spectra")]
pipeline_html_parts = []
for lbl, desc, key in _STAGE_KEYS:
    done  = key in done_steps
    color = "#55efc4" if done else "#636e72"
    icon  = "✅" if done else "⬜"
    pipeline_html_parts.append(
        f"<span style='color:{color};font-weight:bold;background:#2d3436;"
        f"padding:6px 12px;border-radius:6px;'>{icon} {lbl} — {desc}</span>"
    )
pipeline_html = "".join(pipeline_html_parts)

# KPIs HTML
kpi_items: list[tuple[str, str]] = [("Dataset", ds_name), ("Trazas", str(len(traces)))]
if not df_ims.empty:
    if pga_col and not df_ims[pga_col].dropna().empty:
        kpi_items.append(("PGA máx", f"{df_ims[pga_col].dropna().max():.2f} cm/s²"))
    if pgv_col and not df_ims[pgv_col].dropna().empty:
        kpi_items.append(("PGV máx", f"{df_ims[pgv_col].dropna().max():.3f} cm/s"))
    if arias_col and not df_ims[arias_col].dropna().empty:
        kpi_items.append(("I_A máx", f"{df_ims[arias_col].dropna().max():.4f} m/s"))
if hvsr_result:
    kpi_items.append(("f₀ HVSR", f"{hvsr_result.f0_hz:.3f} Hz"))
    kpi_items.append(("T₀", f"{hvsr_result.t0_s:.3f} s"))
kpi_items.append(("Generado", generated_at))

kpi_html = "".join(
    f"<div class='kpi'><div class='val'>{v}</div><div class='lbl'>{k}</div></div>"
    for k, v in kpi_items
)

if st.button("🔄 Generar informe HTML", type="primary", use_container_width=True):
    with st.spinner("Generando informe…"):
        try:
            html_report = _build_html_report(
                ds_name=ds_name,
                generated_at=generated_at,
                pipeline_html=pipeline_html,
                kpi_html=kpi_html,
                df_ims=df_ims,
                fig_waveform=fig_waveform,
                fig_fft=fig_fft,
                fig_psd=fig_psd,
                response_spec_data=response_spec_data,
                hvsr_result=hvsr_result,
                rotd_result=rotd_result,
                picks=picks,
                ai_results=ai_results,
                df_hist=df_hist,
                cosmos_mode=(report_mode == "cosmos"),
                cover_page=(
                    {
                        "report_number": report_number,
                        "project_name": project_name,
                        "site_name": site_name,
                        "event_desc": event_desc,
                        "analyst": analyst,
                        "report_date": str(report_date_val),
                        "latitude": latitude,
                        "longitude": longitude,
                    }
                    if report_mode == "cosmos" else None
                ),
            )
            st.session_state["_report_html"] = html_report
            st.success("Informe generado. Usa el botón de descarga.")
        except Exception as exc:
            st.error(f"Error al generar el informe: {exc}")

report_html = st.session_state.get("_report_html")
if report_html:
    fname_report = f"informe_{ds_name.replace(' ', '_')}_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M')}.html"
    st.download_button(
        "⬇️ Descargar informe HTML",
        data=report_html.encode("utf-8"),
        file_name=fname_report,
        mime="text/html",
        use_container_width=True,
    )
    with st.expander("Vista previa del HTML (primeras 80 líneas)", expanded=False):
        lines = report_html.split("\n")[:80]
        st.code("\n".join(lines), language="html")

# Excel con tabla de IMs como backup rápido
if not df_ims.empty:
    try:
        buf_xl = io.BytesIO()
        with pd.ExcelWriter(buf_xl, engine="openpyxl") as writer:
            df_ims.to_excel(writer, sheet_name="IMs")
            if picks:
                pd.DataFrame(picks).to_excel(writer, sheet_name="Picks_PS", index=False)
            if df_hist is not None:
                df_hist.head(5000).to_excel(writer, sheet_name="Telemetria", index=False)
        st.download_button(
            "⬇️ Descargar Excel (IMs + picks + telemetría)",
            data=buf_xl.getvalue(),
            file_name=f"datos_{ds_name.replace(' ', '_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_report_excel",
        )
    except ImportError:
        st.caption("Instala `openpyxl` para la exportación a Excel.")

# ─────────────────────────────────────────────────────────────────────────────
# EXPORTACIÓN BATCH (ZIP con todos los datasets)
# ─────────────────────────────────────────────────────────────────────────────
all_datasets = list_dataset_names()
if len(all_datasets) > 1:
    st.divider()
    st.subheader("📦 Exportación Batch")
    st.caption(
        f"{len(all_datasets)} datasets en sesión. "
        "Genera un ZIP con una tabla de IMs (Excel) por cada dataset."
    )

    if st.button("⬇️ Generar ZIP con todos los datasets", use_container_width=True):
        ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M")
        zip_buf = io.BytesIO()
        errors: list[str] = []

        with zipfile.ZipFile(zip_buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for ds in all_datasets:
                try:
                    stream_ds = set_current_stream(ds)
                    if stream_ds is None:
                        errors.append(f"{ds}: stream no disponible en caché")
                        continue
                    df_ds = _ims_dataframe(stream_ds)
                    if df_ds.empty:
                        errors.append(f"{ds}: sin IMs calculables")
                        continue
                    xl_buf = io.BytesIO()
                    with pd.ExcelWriter(xl_buf, engine="openpyxl") as writer:
                        df_ds.to_excel(writer, sheet_name="IMs")
                    safe_name = ds.replace(" ", "_").replace("/", "_")[:60]
                    zf.writestr(f"{safe_name}_IMs.xlsx", xl_buf.getvalue())
                except Exception as exc:
                    errors.append(f"{ds}: {exc}")

            # Restaurar dataset original
            set_current_stream(ds_name)

        if errors:
            for err in errors:
                st.warning(f"Omitido — {err}")

        zip_bytes = zip_buf.getvalue()
        if zip_bytes:
            st.download_button(
                "⬇️ Descargar ZIP",
                data=zip_bytes,
                file_name=f"batch_IMs_{ts}.zip",
                mime="application/zip",
                use_container_width=True,
                key="dl_batch_zip",
            )
