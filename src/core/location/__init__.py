"""Location module — 1D grid search utilities (now with 3D support)."""
from .one_d_location import (
    OneDVelocityModel,
    Station,
    PSObservation,
    LocationResult,
    locate_event_1d,
    _dist_3d,
    _estimate_t0,
)