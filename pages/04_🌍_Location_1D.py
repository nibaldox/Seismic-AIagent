import streamlit as st
import numpy as np
from typing import List

from src.streamlit_utils.session_state import get_session, list_picks
from src.core.location import OneDVelocityModel, Station, PSObservation, locate_event_1d
from src.utils.geo import latlon_to_local_xy

st.set_page_config(page_title="Localización 1D", page_icon="🌍")


def _collect_ps_observations(picks: List[dict]):
    # Agrupar picks por estación para extraer pares P/S
    station_map = {}
    for p in picks:
        st_code = p.get("station") or "UNK"
        station_map.setdefault(st_code, {})[p.get("phase")] = p
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


def main():
    st.title("🌍 Localización 1D (Experimental)")
    session = get_session()
    # Obtener picks desde el helper de sesión (evita errores por acceso directo)
    picks = list_picks(session=session)

    st.markdown(
        "Esta herramienta realiza una búsqueda en grid superficial (z=0) asumiendo un medio homogéneo con velocidades constantes para P y S. Resultado es altamente preliminar."
    )

    if not picks:
        st.info("No hay picks en la sesión. Vuelve cuando hayas definido P y S en la vista de waveforms.")
        return

    observations = _collect_ps_observations(picks)
    if len(observations) < 2:
        st.warning("Se requieren al menos 2 estaciones con pares P/S para intentar localización.")
        return

    with st.sidebar:
        st.header("Parámetros")
        vp = st.number_input("Vp (km/s)", value=6.0, min_value=3.0, max_value=8.5, step=0.1)
        vs = st.number_input("Vs (km/s)", value=3.5, min_value=1.5, max_value=5.0, step=0.1)
        grid_span = st.number_input("Extensión ± (km)", value=50.0, min_value=5.0, max_value=500.0, step=5.0)
        grid_step = st.number_input("Paso grid (km)", value=5.0, min_value=0.5, max_value=20.0, step=0.5)
        st.subheader("Estaciones")
        observed_codes = sorted({(o.station or "UNK") for o in observations})
        use_geo = st.checkbox("Usar proyección geográfica (lat/lon → km)", value=True)

        # Intentar leer la última metadata Kelunji (referencia lat/lon)
        meta = session.metadata.get("kelunji_last") if session else None
        ref_lat = ref_lon = None
        if isinstance(meta, dict):
            try:
                ref_lat = float(str(meta.get("lat")).strip()) if meta.get("lat") is not None else None
                ref_lon = float(str(meta.get("long")).strip()) if meta.get("long") is not None else None
            except Exception:
                ref_lat = ref_lon = None
        if ref_lat is None or ref_lon is None:
            st.caption("No hay lat/lon en metadata. Puedes ingresarlas manualmente o usar disposición sintética.")
            ref_lat = st.number_input("Latitud referencia", value=0.0, format="%0.6f")
            ref_lon = st.number_input("Longitud referencia", value=0.0, format="%0.6f")

        stations = []
        if use_geo:
            st.caption("Ingresa lat/lon por estación; se proyectarán respecto a la referencia.")
            for code in observed_codes:
                lat = st.number_input(f"Lat {code}", value=ref_lat, format="%0.6f", key=f"lat_{code}")
                lon = st.number_input(f"Lon {code}", value=ref_lon, format="%0.6f", key=f"lon_{code}")
                try:
                    x_km, y_km = latlon_to_local_xy(lat, lon, ref_lat, ref_lon)
                except Exception:
                    x_km, y_km = 0.0, 0.0
                stations.append(Station(code=code, x=float(x_km), y=float(y_km)))
        else:
            st.caption("Disposición sintética en círculo alrededor del origen (0,0).")
            n_st = max(1, len(observed_codes))
            angles = np.linspace(0, 2 * np.pi, n_st, endpoint=False)
            radius = 20.0  # km
            for ang, code in zip(angles, observed_codes):
                stations.append(
                    Station(
                        code=code,
                        x=float(radius * np.cos(ang)),
                        y=float(radius * np.sin(ang)),
                    )
                )
        st.write("Estaciones (x,y km):")
        for s in stations:
            st.write(f"{s.code}: ({s.x:.3f}, {s.y:.3f})")

    model = OneDVelocityModel(vp=vp, vs=vs)

    if st.button("Calcular Localización"):
        result = locate_event_1d(
            stations=stations,
            observations=observations,
            model=model,
            grid_x=(-grid_span, grid_span, grid_step),
            grid_y=(-grid_span, grid_span, grid_step),
        )
        if result is None:
            st.error("No se pudo localizar (datos insuficientes o residuales inválidos)")
        else:
            st.success(
                f"Epicentro aproximado: x={result.x:.1f} km, y={result.y:.1f} km | t0={result.t0:.2f}s | RMS={result.rms:.3f}s"
            )
            st.write("Residuales:")
            for st_code, res in result.residuals:
                st.write(f"{st_code}: {res:+.3f} s")
