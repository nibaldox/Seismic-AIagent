"""Simple 1D (horizontal) earthquake location by P-S differential times.
Now also supports 3D grid search including depth (z-axis).

Simplificaciones (3D MVP):
- Se asume terreno plano para estaciones (z=0 para estaciones superficiales).
- Se permite profundidad variable para el hipocentro.
- Modelo de velocidades homogéneas (Vp, Vs constantes en todo el dominio).
- No se modelan interfases de velocidad ni gradient.
- Para深度 > 0, la distancia euclidiana es sqrt(dx²+dy²+z²).

Limitaciones: Muy simplificado; no apto para publicación científica sin extender
a modelo 1D layer-cake, correcciones de estación y ajuste conjunto no lineal.
"""
from __future__ import annotations
from dataclasses import dataclass, field
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
    z: float = 0.0  # km (elevación, típica 0 para estaciones superficiales)

@dataclass
class PSObservation:
    station: Station
    t_p: float  # s relativo a inicio registro
    t_s: float  # s relativo a inicio registro

@dataclass
class LocationResult:
    x: float
    y: float
    z: float  # km de profundidad (>0 = más profundo)
    t0: float
    rms: float
    residuals: List[Tuple[str, float]]
    used_stations: int
    notes: str


def _estimate_t0(dist_km: float, obs: PSObservation, model: OneDVelocityModel) -> Tuple[float, float]:
    """Return (t0_from_P, t0_from_S) given a 3D epicentral distance."""
    t0_p = obs.t_p - dist_km / model.vp
    t0_s = obs.t_s - dist_km / model.vs
    return t0_p, t0_s


def _dist_3d(station: Station, x: float, y: float, z: float) -> float:
    """Euclidean distance from (x,y,z) to station in 3D."""
    return np.sqrt((station.x - x) ** 2 + (station.y - y) ** 2 + (station.z - z) ** 2)


def locate_event_1d(
    stations: Iterable[Station],
    observations: Iterable[PSObservation],
    model: OneDVelocityModel,
    *,
    grid_x: Tuple[float, float, float] = (-50, 50, 2.0),
    grid_y: Tuple[float, float, float] = (-50, 50, 2.0),
    grid_z: Tuple[float, float, float] = (-20, 0, 2.0),
    min_stations: int = 2,
) -> Optional[LocationResult]:
    """Grid search 3D (x, y, z).

    Parámetros:
      stations: lista de estaciones con coordenadas (km) en sistema local.
      observations: P-S picks (tP, tS) por estación.
      model: velocidades homogéneas.
      grid_x, grid_y, grid_z: (min, max, step) km.
        - Para búsqueda 2D, usar grid_z=(0, 0, 1) para forzar z=0.
        - Para 3D, grid_z típico: (-20, 0, 2) o (-30, 0, 1).

    Devuelve LocationResult con z (profundidad) o None si insuficiente.
    """
    obs_list = list(observations)
    if len(obs_list) < min_stations:
        return None

    st_map = {s.code: s for s in stations}
    valid_obs = [
        o for o in obs_list
        if isinstance(o.station, Station) and o.station.code in st_map and o.t_s > o.t_p
    ]
    if len(valid_obs) < min_stations:
        return None

    gx = np.arange(grid_x[0], grid_x[1] + 1e-9, grid_x[2])
    gy = np.arange(grid_y[0], grid_y[1] + 1e-9, grid_y[2])
    gz = np.arange(grid_z[0], grid_z[1] + 1e-9, grid_z[2])

    best: Optional[LocationResult] = None

    for x in gx:
        for y in gy:
            for z in gz:
                t0_candidates = []
                residuals = []
                used = 0
                for o in valid_obs:
                    dist = _dist_3d(o.station, x, y, z)
                    t0_p, t0_s = _estimate_t0(dist, o, model)
                    if np.isfinite(t0_p):
                        t0_candidates.append(t0_p)
                    if np.isfinite(t0_s):
                        t0_candidates.append(t0_s)
                if not t0_candidates:
                    continue
                t0 = float(np.median(t0_candidates))
                for o in valid_obs:
                    dist = _dist_3d(o.station, x, y, z)
                    tP_pred = t0 + dist / model.vp
                    residuals.append((o.station.code, o.t_p - tP_pred))
                    used += 1
                if used == 0:
                    continue
                rms = float(np.sqrt(np.mean([r[1] ** 2 for r in residuals])))
                if best is None or rms < best.rms:
                    notes = (
                        f"3D homogéneo (z={z:.1f} km)"
                        if z != 0
                        else "2D homogéneo (z=0 forzado)"
                    )
                    best = LocationResult(x, y, z, t0, rms, residuals, used, notes)

    return best