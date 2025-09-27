"""Geodesy helpers: lat/lon to local tangent plane (ENU) using pyproj.

If pyproj is missing at runtime, functions raise ImportError with guidance.
"""
from __future__ import annotations
from typing import Tuple

try:  # pragma: no cover
    from pyproj import CRS, Transformer
except Exception as exc:  # pragma: no cover
    CRS = None  # type: ignore
    Transformer = None  # type: ignore


def _ensure_pyproj():
    if CRS is None or Transformer is None:
        raise ImportError("pyproj is required for geographic projections. Please install 'pyproj'.")


def latlon_to_local_xy(lat: float, lon: float, lat0: float, lon0: float) -> Tuple[float, float]:
    """Project (lat, lon) to a local ENU-like planar system centered at (lat0, lon0).

    Returns (x_km, y_km), where x is Easting in km and y is Northing in km.
    Uses an azimuthal equidistant projection centered at the reference.
    """
    _ensure_pyproj()
    # Define local azimuthal equidistant centered at origin (lat0, lon0)
    crs_geodetic = CRS.from_epsg(4326)  # WGS84
    crs_local = CRS.from_proj4(f"+proj=aeqd +lat_0={lat0} +lon_0={lon0} +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs")
    transformer = Transformer.from_crs(crs_geodetic, crs_local, always_xy=True)
    x_m, y_m = transformer.transform(lon, lat)
    return x_m / 1000.0, y_m / 1000.0
