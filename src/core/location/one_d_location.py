"""Simple 1D (horizontal) earthquake location by P-S differential times.

Simplificaciones:
- Se asume terreno plano (z=0 fuente y estaciones) -> solo epicentro 2D.
- Hipocentro superficial (depth = 0 km) (puede ampliarse luego a grid 3D).
- Se usa modelo de velocidades constantes Vp, Vs en todo el dominio.
- Observaciones: para cada estación se requiere (tP, tS) relativos al mismo origen de la traza.
- El tiempo origen (t0) se estima minimizando residuales entre tiempos observados y predichos.

Metodología:
1. Para cada punto de un grid (x,y) se calcula distancia a cada estación.
2. Con Vp, Vs se derivan tiempos de viaje teóricos P y S: tP = R/Vp, tS = R/Vs.
3. Para cada estación se puede construir un tiempo origen candidato: t0_i = tP_obs - R/Vp (o usando S), se promedia robustamente.
4. Se computan residuales y un RMS global. Se selecciona el punto con menor RMS.

Limitaciones: Muy simplificado; no apto para publicación científica sin extender a profundidad, 1D layer cake, correcciones de estación y ajuste conjunto no lineal.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Optional, Iterable
import numpy as np

@dataclass
class OneDVelocityModel:
    vp: float  # km/s
    vs: float  # km/s

@dataclass
class Station:
    code: str
    x: float  # km en proyección local
    y: float  # km

@dataclass
class PSObservation:
    station: str
    t_p: float  # s relativo a inicio registro
    t_s: float  # s relativo a inicio registro

@dataclass
class LocationResult:
    x: float
    y: float
    t0: float
    rms: float
    residuals: List[Tuple[str, float]]
    used_stations: int
    notes: str


def _estimate_t0(dist_km: float, obs: PSObservation, model: OneDVelocityModel) -> Tuple[float, float]:
    """Return (t0_from_P, t0_from_S)."""
    t0_p = obs.t_p - dist_km / model.vp
    t0_s = obs.t_s - dist_km / model.vs
    return t0_p, t0_s


def locate_event_1d(
    stations: Iterable[Station],
    observations: Iterable[PSObservation],
    model: OneDVelocityModel,
    *,
    grid_x: Tuple[float, float, float] = (-50, 50, 2.0),
    grid_y: Tuple[float, float, float] = (-50, 50, 2.0),
    min_stations: int = 2,
) -> Optional[LocationResult]:
    """Grid search superficial.

    Parámetros:
      stations: lista de estaciones con coordenadas (km) en sistema local.
      observations: P-S picks (tP, tS) por estación.
      model: velocidades homogéneas.
      grid_x, grid_y: (min, max, step) km.

    Devuelve LocationResult o None si insuficiente.
    """
    obs_list = list(observations)
    if len(obs_list) < min_stations:
        return None

    # Map station -> (x,y)
    st_map = {s.code: s for s in stations}
    # Filtrar observaciones válidas
    valid_obs = [o for o in obs_list if o.station in st_map and o.t_s > o.t_p]
    if len(valid_obs) < min_stations:
        return None

    gx = np.arange(grid_x[0], grid_x[1] + 1e-9, grid_x[2])
    gy = np.arange(grid_y[0], grid_y[1] + 1e-9, grid_y[2])

    best: Optional[LocationResult] = None

    for x in gx:
        for y in gy:
            t0_candidates = []
            residuals = []
            used = 0
            for o in valid_obs:
                st = st_map[o.station]
                dist = np.hypot(st.x - x, st.y - y)
                t0_p, t0_s = _estimate_t0(dist, o, model)
                # Usamos ambos si tienen sentido
                if np.isfinite(t0_p):
                    t0_candidates.append(t0_p)
                if np.isfinite(t0_s):
                    t0_candidates.append(t0_s)
            if len(t0_candidates) == 0:
                continue
            # Estimar t0 robusto (mediana)
            t0 = float(np.median(t0_candidates))
            # Calcular residuales versus tP
            for o in valid_obs:
                st = st_map[o.station]
                dist = np.hypot(st.x - x, st.y - y)
                tP_pred = t0 + dist / model.vp
                res = o.t_p - tP_pred
                residuals.append((o.station, res))
                used += 1
            if used == 0:
                continue
            rms = float(np.sqrt(np.maximum(np.mean([r[1] ** 2 for r in residuals]), 0.0)))
            if best is None or rms < best.rms:
                best = LocationResult(x, y, t0, rms, residuals, used, "OK (superficial homogéneo)")
    return best
