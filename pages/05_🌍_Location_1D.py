import streamlit as st
import numpy as np
from typing import List

from src.streamlit_utils.session_state import (
    get_session, list_picks, add_pick, clear_picks,
    validate_picks_consistency, validate_localization_ready,
)
from src.core.location import OneDVelocityModel, Station, PSObservation, locate_event_1d
from src.utils.geo import latlon_to_local_xy
from src.core.picking import suggest_picks_sta_lta, Pick

st.set_page_config(page_title="Localización 1D", page_icon="🌍", layout="wide")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_phase(phase: str) -> str:
    """Strip trailing '?' so 'P?' and 'S?' match as 'P' and 'S'."""
    return phase.strip().upper().rstrip("?")


def _collect_ps_observations(picks: List[dict]) -> List[PSObservation]:
    """Group picks by station and build P/S pairs. Accepts 'P?'/'S?' phases."""
    station_map: dict = {}
    for p in picks:
        st_code = p.get("station") or "UNK"
        phase_norm = _normalize_phase(p.get("phase", ""))
        if phase_norm in ("P", "S"):
            station_map.setdefault(st_code, {})[phase_norm] = p

    observations = []
    for st_code, phases in station_map.items():
        if "P" in phases and "S" in phases:
            p_pick = phases["P"]
            s_pick = phases["S"]
            if float(s_pick["time_rel"]) > float(p_pick["time_rel"]):
                observations.append(
                    PSObservation(
                        station=st_code,
                        t_p=float(p_pick["time_rel"]),
                        t_s=float(s_pick["time_rel"]),
                    )
                )
    return observations


def _auto_detect_picks(session) -> int:
    """Run STA/LTA on all traces in the current stream and store picks in session.

    Returns number of new picks added.
    """
    from src.streamlit_utils.session_state import get_current_stream

    stream = get_current_stream(session)
    if stream is None or len(stream) == 0:
        return 0

    existing = list_picks(session=session) or []
    existing_keys = {(p.get("station"), _normalize_phase(p.get("phase", ""))) for p in existing}

    added = 0
    for trace in stream:
        try:
            suggestions = suggest_picks_sta_lta(trace, prefilter=True, suggest_s=True)
            stats = getattr(trace, "stats", None)
            station = str(getattr(stats, "station", "UNK"))
            channel = str(getattr(stats, "channel", "?"))
            for s in suggestions:
                phase_raw = s.get("phase", "P?")
                phase_norm = _normalize_phase(phase_raw)
                if (station, phase_norm) in existing_keys:
                    continue
                add_pick(
                    phase=phase_raw,
                    time_rel=float(s["time_rel"]),
                    station=station,
                    channel=channel,
                    method="STA/LTA",
                    session=session,
                )
                existing_keys.add((station, phase_norm))
                added += 1
        except Exception:
            continue

    return added


def _plot_result(result, stations, observations) -> None:
    """Render epicenter + stations scatter plot with Plotly."""
    try:
        import plotly.graph_objects as go

        fig = go.Figure()

        # Grid RMS heatmap placeholder (just stations + epicenter for now)
        # --- Stations ---
        st_x = [s.x for s in stations]
        st_y = [s.y for s in stations]
        st_labels = [s.code for s in stations]
        fig.add_trace(go.Scatter(
            x=st_x, y=st_y, mode="markers+text",
            marker=dict(symbol="triangle-up", size=14, color="#4f8ef7"),
            text=st_labels, textposition="top center",
            name="Estaciones",
        ))

        # --- Epicenter ---
        fig.add_trace(go.Scatter(
            x=[result.x], y=[result.y], mode="markers",
            marker=dict(symbol="star", size=20, color="#f87171"),
            name=f"Epicentro (RMS={result.rms:.3f}s)",
        ))

        # --- P-S rays ---
        for obs in observations:
            st_obj = next((s for s in stations if s.code == obs.station), None)
            if st_obj:
                fig.add_trace(go.Scatter(
                    x=[result.x, st_obj.x], y=[result.y, st_obj.y],
                    mode="lines",
                    line=dict(color="#9ca3af", dash="dot", width=1),
                    showlegend=False,
                ))

        fig.update_layout(
            template="plotly_dark",
            title=f"Epicentro: ({result.x:.1f}, {result.y:.1f}) km | t₀={result.t0:.2f}s | RMS={result.rms:.3f}s",
            xaxis_title="X (km Este)",
            yaxis_title="Y (km Norte)",
            yaxis_scaleanchor="x",
            height=480,
            margin=dict(l=40, r=40, t=50, b=40),
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as exc:
        st.warning(f"No se pudo graficar el resultado: {exc}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    st.title("🌍 Localización 1D (Experimental)")
    session = get_session()

    st.markdown(
        "Búsqueda en grid superficial (z=0) con modelo homogéneo P/S. "
        "Resultado es orientativo — no apto para publicación sin correcciones adicionales."
    )

    # ── Auto-detect picks ──────────────────────────────────────────────────
    st.subheader("1. Picks P/S")

    picks = list_picks(session=session) or []

    col_auto, col_clear = st.columns([2, 1])
    with col_auto:
        if st.button("🔍 Detectar picks automáticamente (STA/LTA)", use_container_width=True):
            n = _auto_detect_picks(session)
            if n > 0:
                st.success(f"{n} pick(s) nuevos detectados y guardados en sesión.")
                picks = list_picks(session=session) or []
            else:
                st.warning("No se detectaron picks nuevos (puede que ya existan o no haya datos cargados).")
    with col_clear:
        if st.button("🗑️ Limpiar picks", use_container_width=True):
            clear_picks(session=session)
            picks = []
            st.rerun()

    if picks:
        # Mostrar tabla de picks
        import pandas as pd
        df = pd.DataFrame([{
            "Fase": p.get("phase", "?"),
            "Estación": p.get("station", "?"),
            "Canal": p.get("channel", "?"),
            "t_rel (s)": f"{float(p.get('time_rel', 0)):.3f}",
            "SNR (dB)": f"{p.get('snr_db', '-'):.1f}" if p.get("snr_db") is not None else "—",
            "Método": p.get("method", "manual"),
        } for p in picks])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Sin picks en sesión. Usa el botón de detección automática o agrega picks desde el Waveform Viewer.")
        return

    # Validaciones pre-localización
    consistency_warnings = validate_picks_consistency(session=session)
    for w in consistency_warnings:
        st.warning(f"⚠️ {w}")

    ready, loc_reasons = validate_localization_ready(session=session)
    for reason in loc_reasons:
        if ready:
            st.warning(f"⚠️ {reason}")
        else:
            st.error(f"🚫 {reason}")
    if not ready:
        return

    observations = _collect_ps_observations(picks)
    if len(observations) == 0:
        st.warning(
            "No se encontraron pares P/S por estación. "
            "Se necesita al menos una estación con pick P y pick S para localizar."
        )
        return

    st.caption(f"Pares P/S disponibles: {len(observations)} estación(es) — {[o.station for o in observations]}")

    # ── Parámetros ────────────────────────────────────────────────────────
    st.subheader("2. Parámetros de localización")

    with st.sidebar:
        st.header("Parámetros")
        vp = st.number_input("Vp (km/s)", value=6.0, min_value=3.0, max_value=8.5, step=0.1)
        vs = st.number_input("Vs (km/s)", value=3.5, min_value=1.5, max_value=5.0, step=0.1)
        grid_span = st.number_input("Extensión ± (km)", value=50.0, min_value=5.0, max_value=500.0, step=5.0)
        grid_step = st.number_input("Paso grid (km)", value=2.0, min_value=0.5, max_value=20.0, step=0.5)

        st.subheader("Estaciones")
        observed_codes = sorted({o.station for o in observations})
        use_geo = st.checkbox("Usar proyección geográfica (lat/lon → km)", value=True)

        meta = session.metadata.get("kelunji_last") if session else None
        ref_lat = ref_lon = None
        if isinstance(meta, dict):
            try:
                ref_lat = float(str(meta.get("lat")).strip()) if meta.get("lat") is not None else None
                ref_lon = float(str(meta.get("long")).strip()) if meta.get("long") is not None else None
            except Exception:
                ref_lat = ref_lon = None
        if ref_lat is None or ref_lon is None:
            st.caption("No hay lat/lon en metadata. Ingrésalas manualmente.")
            ref_lat = st.number_input("Latitud referencia", value=-33.45, format="%0.6f")
            ref_lon = st.number_input("Longitud referencia", value=-70.65, format="%0.6f")

        stations: List[Station] = []
        if use_geo:
            st.caption("Ingresa lat/lon por estación:")
            for code in observed_codes:
                lat = st.number_input(f"Lat {code}", value=ref_lat, format="%0.6f", key=f"lat_{code}")
                lon = st.number_input(f"Lon {code}", value=ref_lon, format="%0.6f", key=f"lon_{code}")
                try:
                    x_km, y_km = latlon_to_local_xy(lat, lon, ref_lat, ref_lon)
                except Exception:
                    x_km, y_km = 0.0, 0.0
                stations.append(Station(code=code, x=float(x_km), y=float(y_km)))
        else:
            st.caption("Disposición sintética en círculo (r=20 km).")
            n_st = max(1, len(observed_codes))
            angles = np.linspace(0, 2 * np.pi, n_st, endpoint=False)
            for ang, code in zip(angles, observed_codes):
                stations.append(Station(code=code, x=float(20.0 * np.cos(ang)), y=float(20.0 * np.sin(ang))))

        st.write("Estaciones (x,y km):")
        for s in stations:
            st.write(f"**{s.code}**: ({s.x:.3f}, {s.y:.3f})")

    # ── Localizar ─────────────────────────────────────────────────────────
    st.subheader("3. Resultado")

    if len(observations) < 2:
        st.warning("Se requieren al menos 2 estaciones con pares P/S.")
        return

    model = OneDVelocityModel(vp=vp, vs=vs)

    if st.button("📍 Calcular Localización", type="primary", use_container_width=True):
        with st.spinner("Buscando en grid..."):
            result = locate_event_1d(
                stations=stations,
                observations=observations,
                model=model,
                grid_x=(-grid_span, grid_span, grid_step),
                grid_y=(-grid_span, grid_span, grid_step),
            )
        if result is None:
            st.error("No se pudo localizar (datos insuficientes o residuales inválidos).")
        else:
            st.success(
                f"Epicentro: x={result.x:.1f} km, y={result.y:.1f} km | "
                f"t₀={result.t0:.2f} s | RMS={result.rms:.3f} s | "
                f"Estaciones usadas: {result.used_stations}"
            )

            # ts-tp estimado para información
            if observations:
                avg_tstp = np.mean([o.t_s - o.t_p for o in observations])
                dist_est = avg_tstp / (1.0 / vp - 1.0 / vs)
                st.info(f"ts-tp promedio: {avg_tstp:.2f} s → distancia estimada: ~{dist_est:.1f} km")

            _plot_result(result, stations, observations)

            st.subheader("Residuales por estación")
            import pandas as pd
            res_df = pd.DataFrame([
                {"Estación": st_code, "Residual P (s)": f"{res:+.3f}"}
                for st_code, res in result.residuals
            ])
            st.dataframe(res_df, use_container_width=True, hide_index=True)


main()
