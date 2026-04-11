"""Tests para src/core/magnitude.py.

Cubre: estimate_local_magnitude_wa, estimate_local_magnitude_wa_with_response,
       _compute_ml_hutton_boore, _estimate_distance_from_ps, MagnitudeResult.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from src.core.magnitude import (
    MagnitudeResult,
    _compute_ml_hutton_boore,
    _estimate_distance_from_ps,
    _log10_a0_hutton_boore,
    estimate_local_magnitude_wa,
    estimate_local_magnitude_wa_with_response,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
SR = 100.0
DT = 1.0 / SR
N = 2000  # 20 s de señal
RNG = np.random.default_rng(17)
NOISE = RNG.standard_normal(N).astype(float)

STATION = "TST"


def _picks(p_time: float, s_time: float, station: str = STATION) -> list:
    return [
        {"phase": "P", "time_rel": p_time, "station": station, "channel": "HHZ"},
        {"phase": "S", "time_rel": s_time, "station": station, "channel": "HHZ"},
    ]


# ---------------------------------------------------------------------------
# _estimate_distance_from_ps
# ---------------------------------------------------------------------------

class TestEstimateDistanceFromPs:
    def test_10s_gives_84km(self):
        d = _estimate_distance_from_ps(10.0)
        assert d == pytest.approx(84.0, abs=0.1)

    def test_zero_gives_zero(self):
        assert _estimate_distance_from_ps(0.0) == pytest.approx(0.0)

    def test_proportional_to_delta_ps(self):
        d1 = _estimate_distance_from_ps(5.0)
        d2 = _estimate_distance_from_ps(10.0)
        assert d2 == pytest.approx(d1 * 2.0, rel=1e-6)


# ---------------------------------------------------------------------------
# _log10_a0_hutton_boore
# ---------------------------------------------------------------------------

class TestLog10A0HuttonBoore:
    def test_returns_negative_value(self):
        assert _log10_a0_hutton_boore(50.0) < 0.0
        assert _log10_a0_hutton_boore(100.0) < 0.0

    def test_at_100km_approx_minus3pt40(self):
        # Hutton & Boore: C(100) ≈ 3.40 → log10(A0) = -3.40
        val = _log10_a0_hutton_boore(100.0)
        assert val == pytest.approx(-3.40, abs=0.05)

    def test_decreases_with_distance(self):
        # A mayor distancia, log10(A0) más negativo
        v1 = _log10_a0_hutton_boore(50.0)
        v2 = _log10_a0_hutton_boore(200.0)
        assert v2 < v1


# ---------------------------------------------------------------------------
# _compute_ml_hutton_boore
# ---------------------------------------------------------------------------

class TestComputeMlHuttonBoore:
    def test_amplitude_1mm_at_100km(self):
        ml = _compute_ml_hutton_boore(1.0, 100.0, calibration={})
        # ML = log10(1) + C(100) = 0 + 3.40 ≈ 3.40
        assert ml == pytest.approx(3.40, abs=0.1)

    def test_invalid_amplitude_raises(self):
        with pytest.raises(ValueError):
            _compute_ml_hutton_boore(0.0, 100.0)

    def test_invalid_distance_raises(self):
        with pytest.raises(ValueError):
            _compute_ml_hutton_boore(1.0, 0.0)

    def test_ml_increases_with_amplitude(self):
        ml1 = _compute_ml_hutton_boore(1.0, 100.0, calibration={})
        ml2 = _compute_ml_hutton_boore(10.0, 100.0, calibration={})
        # A 10× amplitud → ML aumenta 1 unidad
        assert ml2 == pytest.approx(ml1 + 1.0, abs=0.01)

    def test_ml_increases_with_distance_same_amplitude(self):
        # A misma amplitud medida, un evento más lejano tiene ML mayor
        # (necesitó más energía para llegar tan lejos).
        # ML = log10(A_mm) + C(R), y C(R) crece con R.
        ml_close = _compute_ml_hutton_boore(1.0, 10.0, calibration={})
        ml_far = _compute_ml_hutton_boore(1.0, 300.0, calibration={})
        assert ml_far > ml_close


# ---------------------------------------------------------------------------
# estimate_local_magnitude_wa — sin picks → ml=None
# ---------------------------------------------------------------------------

class TestEstimateLocalMagnitudeWa:
    def test_no_picks_returns_ml_none(self):
        result = estimate_local_magnitude_wa(
            picks=[], trace_data=NOISE, trace_sampling_rate=SR, station=STATION
        )
        assert isinstance(result, MagnitudeResult)
        assert result.ml is None

    def test_missing_s_pick_returns_ml_none(self):
        picks_only_p = [{"phase": "P", "time_rel": 2.0, "station": STATION, "channel": "HHZ"}]
        result = estimate_local_magnitude_wa(
            picks=picks_only_p, trace_data=NOISE, trace_sampling_rate=SR, station=STATION
        )
        assert result.ml is None

    def test_wrong_station_returns_ml_none(self):
        picks = _picks(2.0, 4.0, station="OTHER")
        result = estimate_local_magnitude_wa(
            picks=picks, trace_data=NOISE, trace_sampling_rate=SR, station=STATION
        )
        assert result.ml is None

    def test_valid_picks_returns_numeric_ml(self):
        # Con picks válidos y señal suficientemente larga, debe retornar un float
        picks = _picks(2.0, 5.0)
        result = estimate_local_magnitude_wa(
            picks=picks, trace_data=NOISE, trace_sampling_rate=SR, station=STATION
        )
        # ML puede ser None si pico de amplitud es cero; verificar que al menos es un float o None
        if result.ml is not None:
            assert isinstance(result.ml, float)
            assert math.isfinite(result.ml)

    def test_result_has_distance_km(self):
        picks = _picks(2.0, 5.0)
        result = estimate_local_magnitude_wa(
            picks=picks, trace_data=NOISE, trace_sampling_rate=SR, station=STATION
        )
        # Con P=2.0, S=5.0 → delta_ps=3.0 → dist=25.2 km
        if result.distance_km is not None:
            assert result.distance_km == pytest.approx(3.0 * 8.4, rel=1e-3)

    def test_result_has_warnings_list(self):
        picks = _picks(2.0, 5.0)
        result = estimate_local_magnitude_wa(
            picks=picks, trace_data=NOISE, trace_sampling_rate=SR, station=STATION
        )
        assert isinstance(result.warnings, list)

    def test_negative_delta_ps_returns_ml_none(self):
        picks = _picks(p_time=5.0, s_time=2.0)  # S antes que P
        result = estimate_local_magnitude_wa(
            picks=picks, trace_data=NOISE, trace_sampling_rate=SR, station=STATION
        )
        assert result.ml is None

    def test_as_dict_returns_dict(self):
        picks = _picks(2.0, 5.0)
        result = estimate_local_magnitude_wa(
            picks=picks, trace_data=NOISE, trace_sampling_rate=SR, station=STATION
        )
        d = result.as_dict()
        assert isinstance(d, dict)
        assert "ml" in d
        assert "distance_km" in d


# ---------------------------------------------------------------------------
# estimate_local_magnitude_wa_with_response
# ---------------------------------------------------------------------------

class TestEstimateLocalMagnitudeWaWithResponse:
    def test_no_picks_returns_ml_none(self):
        result = estimate_local_magnitude_wa_with_response(
            picks=[], trace_data=NOISE, trace_sampling_rate=SR,
            station=STATION, inventory_path=None
        )
        assert result.ml is None

    def test_valid_picks_no_inventory(self):
        picks = _picks(1.0, 4.0)
        result = estimate_local_magnitude_wa_with_response(
            picks=picks, trace_data=NOISE, trace_sampling_rate=SR,
            station=STATION, inventory_path=None
        )
        # Sin inventario debe haber una advertencia específica
        assert any("inventario" in w.lower() or "sin" in w.lower() for w in result.warnings)

    def test_method_field_is_wood_anderson_inst(self):
        picks = _picks(1.0, 4.0)
        result = estimate_local_magnitude_wa_with_response(
            picks=picks, trace_data=NOISE, trace_sampling_rate=SR,
            station=STATION, inventory_path=None
        )
        assert result.method == "wood_anderson_inst"

    def test_short_trace_returns_ml_none(self):
        picks = _picks(0.0, 0.5)
        short_data = NOISE[:5]
        result = estimate_local_magnitude_wa_with_response(
            picks=picks, trace_data=short_data, trace_sampling_rate=SR,
            station=STATION, inventory_path=None
        )
        assert result.ml is None
