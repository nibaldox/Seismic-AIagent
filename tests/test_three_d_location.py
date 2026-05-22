"""Test synthetic validation for 3D location."""

from __future__ import annotations

import math
import tempfile
from pathlib import Path

import numpy as np
import pytest

from src.core.location.one_d_location import (
    OneDVelocityModel,
    Station,
    PSObservation,
    locate_event_1d,
)


def _synthetic_times(
    event_x: float,
    event_y: float,
    event_z: float,
    stations: list[Station],
    model: OneDVelocityModel,
    noise_std: float = 0.05,
    seed: int = 42,
) -> list[PSObservation]:
    """Generate synthetic P/S observations with optional Gaussian noise."""
    rng = np.random.default_rng(seed)
    obs = []
    for st in stations:
        dist = math.sqrt((st.x - event_x) ** 2 + (st.y - event_y) ** 2 + event_z**2)
        t_p = dist / model.vp
        t_s = dist / model.vs
        obs.append(
            PSObservation(
                station=st,
                t_p=max(0.0, t_p + rng.normal(0.0, noise_std)),
                t_s=max(t_p + 0.1, t_s + rng.normal(0.0, noise_std)),
            )
        )
    return obs


def _make_stations() -> list[Station]:
    """5 stations in a 20×20 km grid."""
    return [
        Station(code="S1", x=0.0, y=0.0, z=0.0),
        Station(code="S2", x=20.0, y=0.0, z=0.0),
        Station(code="S3", x=10.0, y=20.0, z=0.0),
        Station(code="S4", x=0.0, y=10.0, z=0.0),
        Station(code="S5", x=10.0, y=10.0, z=0.0),
    ]


EVENTS = [
    {"x": 10.0, "y": 10.0, "z": -5.0, "label": "E1-centro-superficial"},
    {"x": 5.0, "y": 15.0, "z": -10.0, "label": "E2-izq-profundo"},
    {"x": 15.0, "y": 5.0, "z": -15.0, "label": "E3-der-mas-profundo"},
]


@pytest.mark.parametrize("event", EVENTS, ids=lambda e: e["label"])
def test_three_d_location_synthetic(event: dict) -> None:
    """Synthetic 3D location: verify depth and RMSE within acceptance criteria."""
    model = OneDVelocityModel(vp=6.0, vs=3.46)
    stations = _make_stations()
    obs = _synthetic_times(
        event_x=event["x"],
        event_y=event["y"],
        event_z=-5.0,
        stations=stations,
        model=model,
        noise_std=0.05,
        seed=42,
    )

    result = locate_event_1d(
        stations=stations,
        observations=obs,
        model=model,
        grid_x=(-25.0, 25.0, 1.0),
        grid_y=(-25.0, 25.0, 1.0),
        grid_z=(-20.0, 20.0, 1.0),
    )

    assert result is not None, f"Location failed for {event['label']}"
    depth_error = abs(result.z - event["z"])
    assert depth_error <= 5.0, (
        f"{event['label']}: depth error {depth_error:.2f} km > 5 km "
        f"(found z={result.z:.2f}, expected {event['z']})"
    )
    assert result.rms <= 0.5, (
        f"{event['label']}: RMS {result.rms:.3f} s > 0.5 s"
    )


def test_three_d_location_noisy_repeatability() -> None:
    """Verify ≥80% pass rate over 10 noisy runs for E1."""
    model = OneDVelocityModel(vp=6.0, vs=3.46)
    stations = _make_stations()
    event = EVENTS[0]

    passes = 0
    trials = 10
    for i in range(trials):
        obs = _synthetic_times(
        event_x=event["x"],
        event_y=event["y"],
        event_z=-5.0,
        stations=stations,
        model=model,
        noise_std=0.05,
        seed=i * 111,
        )
        result = locate_event_1d(
            stations=stations,
            observations=obs,
            model=model,
            grid_x=(-25.0, 25.0, 1.0),
            grid_y=(-25.0, 25.0, 1.0),
            grid_z=(-20.0, 20.0, 1.0),
        )
        if result is not None and abs(result.z - event["z"]) <= 5.0 and result.rms <= 0.5:
            passes += 1

    ratio = passes / trials
    assert ratio >= 0.8, f"Repeatability {ratio:.0%} < 80% (passed {passes}/{trials})"


def test_three_d_station_at_nonzero_depth() -> None:
    """Station at non-zero z (borehole) should still locate correctly."""
    model = OneDVelocityModel(vp=6.0, vs=3.46)
    stations = [
        Station(code="S1", x=0.0, y=0.0, z=0.0),
        Station(code="S2", x=15.0, y=0.0, z=-2.0),
        Station(code="S3", x=0.0, y=15.0, z=0.0),
        Station(code="S4", x=15.0, y=15.0, z=-2.0),
    ]
    event = {"x": 7.5, "y": 7.5, "z": -8.0}
    obs = _synthetic_times(
        event_x=event["x"],
        event_y=event["y"],
        event_z=event["z"],
        stations=stations,
        model=model,
        noise_std=0.03,
        seed=99,
    )
    result = locate_event_1d(
        stations=stations,
        observations=obs,
        model=model,
        grid_x=(-25.0, 25.0, 1.0),
        grid_y=(-25.0, 25.0, 1.0),
        grid_z=(-20.0, 20.0, 1.0),
    )
    assert result is not None
    depth_error = abs(result.z - event["z"])
    assert depth_error <= 5.0, f"Borehole depth error {depth_error:.2f} km > 5 km"


def test_insufficient_stations() -> None:
    """Less than 2 stations should return None gracefully."""
    model = OneDVelocityModel(vp=6.0, vs=3.46)
    stations = [Station(code="S1", x=0.0, y=0.0, z=0.0)]
    obs = _synthetic_times(event_x=10.0, event_y=10.0, event_z=5.0, stations=stations, model=model)
    result = locate_event_1d(stations=stations, observations=obs, model=model)
    assert result is None


def test_2d_forced_with_z_zero() -> None:
    """Forcing z=0 via grid_z=(0,0,1) should recover 2D result."""
    model = OneDVelocityModel(vp=6.0, vs=3.46)
    stations = _make_stations()
    obs = _synthetic_times(
        event_x=10.0, event_y=10.0, event_z=0.0,
        stations=stations, model=model, noise_std=0.02, seed=7,
    )
    result_2d = locate_event_1d(
        stations=stations, observations=obs, model=model,
        grid_x=(-25.0, 25.0, 1.0),
        grid_y=(-25.0, 25.0, 1.0),
        grid_z=(0.0, 0.0, 1.0),  # force z=0
    )
    assert result_2d is not None
    assert abs(result_2d.z) < 0.5, "Forced z=0 should stay near 0"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])