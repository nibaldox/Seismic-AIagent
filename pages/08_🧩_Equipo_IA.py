"""Página: Equipo IA multi‑agente (MVP)."""

from __future__ import annotations

import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from pathlib import Path

from src.ai_agent.seismic_interpreter import load_agent_suite, run_team_analysis
from src.streamlit_utils.appearance import handle_error
from src.streamlit_utils.session_state import get_team_context, get_session

# Load environment variables
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=False)

st.set_page_config(page_title="Equipo IA", page_icon="🧩")


def main() -> None:
    st.header("🧩 Equipo IA (MVP)")
    st.caption("Ejecución orquestada de agentes para producir un informe consolidado.")

    # Contexto mínimo tomado de la página de Histogramas/telemetría
    st.subheader("Contexto de telemetría (opcional)")
    ctx = get_team_context() or {}
    pre_cols = ", ".join(ctx.get("telemetry", {}).get("columns", [])) if ctx.get("telemetry") else "3D peak, Voltage, Temperature"
    pre_range = ctx.get("time_range") or ""
    pre_notes = ctx.get("telemetry", {}).get("notes") or ""
    cols = st.text_input("Columnas (coma separada)", value=pre_cols)
    time_range = st.text_input("Rango temporal (texto)", value=pre_range)
    notes = st.text_area("Notas/ajustes", value=pre_notes)

    st.subheader("Vista previa de datos (opcional)")
    df_text = st.text_area("Pega una tabla pequeña (CSV)")
    df_head_md = ""
    if df_text.strip():
        try:
            from io import StringIO
            tmp = pd.read_csv(StringIO(df_text))
            df_head_md = tmp.head(20).to_markdown(index=False)
            st.dataframe(tmp.head(10))
        except Exception as e:
            st.warning(f"No se pudo parsear CSV: {e}")
    elif ctx.get("telemetry", {}).get("df_head"):
        # Reutilizar la vista previa enviada desde Histogramas
        df_head_md = ctx["telemetry"]["df_head"]
        st.caption("Vista previa reutilizada desde 'Histogramas'.")

    # Parámetros de búsqueda de sismicidad cercana
    with st.expander("Catálogo sísmico cercano (USGS/EMSC)"):
        # Autocompletar coordenadas desde metadatos cargados (Kelunji) si existen
        session = get_session()
        kel = session.metadata.get("kelunji_last") if session else None
        def _parse_float(v):
            try:
                return float(str(v).strip()) if v is not None else None
            except Exception:
                return None
        kel_lat = _parse_float(kel.get("lat")) if isinstance(kel, dict) else None
        kel_lon = _parse_float(kel.get("long")) if isinstance(kel, dict) else None
        stored_lat = session.metadata.get("earthquake_search_lat") if session else None
        stored_lon = session.metadata.get("earthquake_search_lon") if session else None
        if stored_lat is None and kel_lat is not None:
            stored_lat = kel_lat
            session.metadata["earthquake_search_lat"] = stored_lat
        if stored_lon is None and kel_lon is not None:
            stored_lon = kel_lon
            session.metadata["earthquake_search_lon"] = stored_lon
        col1, col2 = st.columns(2)
        with col1:
            lat = st.number_input(
                "Latitud",
                value=float(stored_lat) if stored_lat is not None else float(ctx.get("eq_search", {}).get("latitude", 0.0)),
                min_value=-90.0,
                max_value=90.0,
                format="%.6f",
            )
            radius_km = st.number_input("Radio (km)", min_value=10, max_value=1000, value=int(ctx.get("eq_search", {}).get("radius_km", 100)))
            days = st.number_input("Días hacia atrás", min_value=1, max_value=120, value=int(ctx.get("eq_search", {}).get("days", 30)))
        with col2:
            lon = st.number_input(
                "Longitud",
                value=float(stored_lon) if stored_lon is not None else float(ctx.get("eq_search", {}).get("longitude", 0.0)),
                min_value=-180.0,
                max_value=180.0,
                format="%.6f",
            )
            min_mag = st.number_input("Magnitud mínima", min_value=0.0, max_value=10.0, value=float(ctx.get("eq_search", {}).get("min_magnitude", 2.5)))
        # Persistimos coordenadas para reutilizarlas entre páginas
        session.metadata["earthquake_search_lat"] = lat
        session.metadata["earthquake_search_lon"] = lon
        if kel_lat is not None and kel_lon is not None:
            st.caption("Coordenadas precargadas desde metadatos Kelunji. Ajusta si lo necesitas.")

    # Parámetros del localizador 1D
    with st.expander("Localización 1D (superficial)"):
        colm1, colm2 = st.columns(2)
        with colm1:
            vp = st.number_input("Vp (km/s)", min_value=1.0, max_value=9.0, value=6.0)
            min_st = st.number_input("Mínimo estaciones", min_value=2, max_value=20, value=2)
            grid_x_txt = st.text_input("Grid X (min,max,step km)", value="-50,50,2.0")
        with colm2:
            vs = st.number_input("Vs (km/s)", min_value=0.5, max_value=5.0, value=3.5)
            ref_lat = st.text_input("Ref lat0 (para proyectar estaciones lat/lon)", value="")
            ref_lon = st.text_input("Ref lon0", value="")

        st.markdown("Estaciones (XY km) - CSV con columnas code,x_km,y_km")
        stn_xy_csv = st.text_area("Pegue estaciones XY", key="stations_xy")
        st.markdown("o Estaciones (Lat/Lon) - CSV con columnas code,lat,lon")
        stn_ll_csv = st.text_area("Pegue estaciones lat/lon", key="stations_ll")
        st.markdown("Observaciones P/S - CSV con columnas station,t_p,t_s (seg)")
        obs_csv = st.text_area("Pegue observaciones", key="observations")

    if st.button("🚀 Ejecutar equipo"):
        import time
        agents = load_agent_suite()

        # Build context
        telemetry_ctx = {
            "columns": [c.strip() for c in cols.split(",") if c.strip()],
            "df_head": df_head_md,
            "notes": notes or None,
            "meta": ctx.get("telemetry", {}).get("meta") or {},
            "filename": ctx.get("telemetry", {}).get("filename"),
            "analysis_ts": None,
            "params": None,
        }

        # Parse helpers
        def _parse_tuple3(txt: str, default: tuple[float, float, float]):
            try:
                parts = [p.strip() for p in txt.split(",")]
                return float(parts[0]), float(parts[1]), float(parts[2])
            except Exception:
                return default

        def _parse_csv_optional(txt: str):
            if not txt or not txt.strip():
                return None
            try:
                from io import StringIO
                df = pd.read_csv(StringIO(txt))
                return df.to_dict(orient="records")
            except Exception:
                return None

        eq_ctx = {
            "latitude": lat if lat or lat == 0 else None,
            "longitude": lon if lon or lon == 0 else None,
            "radius_km": int(radius_km),
            "days": int(days),
            "min_magnitude": float(min_mag),
        }

        # Location context
        stations_xy = _parse_csv_optional(stn_xy_csv) or []
        stations_ll = _parse_csv_optional(stn_ll_csv) or []
        observations = _parse_csv_optional(obs_csv) or []
        loc_ctx = {
            "stations_xy": stations_xy if stations_xy else None,
            "stations": stations_ll if (stations_ll and not stations_xy) else None,
            "observations": observations if observations else None,
            "model": {"vp": vp, "vs": vs},
            "grid": {"x": _parse_tuple3(grid_x_txt, (-50.0, 50.0, 2.0)), "y": (-50.0, 50.0, 2.0)},
            "min_stations": int(min_st),
            "reference": {"lat0": float(ref_lat) if ref_lat else None, "lon0": float(ref_lon) if ref_lon else None},
        }

        context = {
            "time_range": time_range or None,
            "telemetry": telemetry_ctx if telemetry_ctx["columns"] or df_head_md else None,
            "waveform_summary": None,
            "eq_search": eq_ctx if eq_ctx.get("latitude") is not None and eq_ctx.get("longitude") is not None else None,
            "location": loc_ctx if (loc_ctx.get("observations") and (loc_ctx.get("stations_xy") or loc_ctx.get("stations"))) else None,
        }

        # Create placeholders for real-time updates
        status_placeholder = st.empty()
        progress_placeholder = st.empty()
        streaming_placeholder = st.empty()

        # --- Instrumentar tiempo de ejecución IA ---
        t0 = time.time()
        with st.spinner("Inicializando equipo de análisis sísmico..."):
            status_placeholder.info("🚀 Iniciando análisis coordinado del equipo IA")

            try:
                result = run_team_analysis(agents, context=context)
                t1 = time.time()
                ia_duration = t1 - t0
                session.metadata["team_ia_metrics"] = {
                    "start": t0,
                    "end": t1,
                    "duration": ia_duration,
                    "agent_count": result.get("agent_count", None),
                    "team_mode": result.get("team_mode", "secuencial"),
                }

                # Clear status
                status_placeholder.empty()

                # Show team capabilities if available
                if result.get("team_capabilities"):
                    with st.expander("🎯 Capacidades del Equipo Utilizadas"):
                        caps = result["team_capabilities"]
                        st.markdown(f"**Modo de coordinación:** {'Coordinado' if 'coordinate_mode' in caps else 'Colaborativo'}")
                        st.markdown(f"**Agentes en equipo:** {result.get('agent_count', 'N/A')}")
                        st.markdown(f"**Duración total:** {result.get('duration', 0):.2f}s")
                        if "streaming_events" in caps:
                            st.markdown(f"**Eventos de streaming:** {result.get('streaming_events', 0)}")
                        st.markdown("**Características activadas:**")
                        for cap in caps:
                            st.markdown(f"- {cap.replace('_', ' ').title()}")

                # Show intermediate steps if available
                if result.get("intermediate_steps"):
                    with st.expander("📊 Pasos Intermedios del Análisis"):
                        steps = result["intermediate_steps"]
                        for i, step in enumerate(steps[:10]):  # Show first 10 steps
                            timestamp = step.get("timestamp", 0)
                            event_type = step.get("event_type", "unknown")
                            agent = step.get("agent", "Sistema")
                            content_preview = step.get("content", "")[:100] + "..." if len(step.get("content", "")) > 100 else step.get("content", "")
                            st.markdown(f"**{i+1}.** `{event_type}` - {agent}: {content_preview}")

                st.subheader("📋 Informe Consolidado")
                st.markdown(result.get("markdown", "(sin contenido)"))

                if result.get("qa"):
                    with st.expander("🔍 Notas de QA (Crítico)"):
                        st.markdown(result["qa"])

                if result.get("facts"):
                    with st.expander("📊 Resumen de Hallazgos (Factbase)"):
                        fb = result["facts"]
                        st.json(fb)

                # Show success message with team info
                team_mode = result.get("team_mode", "secuencial")
                duration = result.get("duration", 0)
                st.success(f"✅ Análisis completado en modo {team_mode} ({duration:.2f}s)")

            except Exception as exc:
                handle_error(exc, context="Error en análisis del equipo IA")
                status_placeholder.error(f"❌ Error en análisis del equipo: {str(exc)}")
                st.error("El sistema ha hecho fallback a modo secuencial. Revisa los logs para más detalles.")

        # --- Panel de métricas IA ---
        ia_metrics = session.metadata.get("team_ia_metrics", {})
        if ia_metrics:
            with st.expander("📈 Métricas de IA (Equipo)"):
                st.metric("Duración total IA (s)", f"{ia_metrics.get('duration', 0):.2f}")
                st.metric("Agentes en equipo", ia_metrics.get("agent_count", "N/A"))
                st.metric("Modo de equipo", ia_metrics.get("team_mode", "N/A"))

        st.caption("💡 Sugerencia: El equipo IA utiliza ahora capacidades avanzadas de Agno Teams para análisis coordinado y streaming en tiempo real.")


if __name__ == "__main__":
    main()
