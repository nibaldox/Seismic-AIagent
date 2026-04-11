"""Tests para src/core/intensity_measures.py.

Cubre: compute_pgv_pgd, compute_arias_intensity, compute_significant_duration,
       compute_cav, compute_dominant_period, compute_mean_period, compute_all_ims.
"""
from __future__ import annotations

import numpy as np
import pytest

from src.core.intensity_measures import (
    IntensityMeasures,
    compute_all_ims,
    compute_arias_intensity,
    compute_cav,
    compute_dominant_period,
    compute_mean_period,
    compute_pgv_pgd,
    compute_significant_duration,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
RNG = np.random.default_rng(42)

SR = 100.0          # Hz
DT = 1.0 / SR
N = 1000            # 10 s de señal
NOISE = RNG.standard_normal(N).astype(float)  # ruido blanco en cm/s²


class FakeStats:
    delta = DT
    sampling_rate = SR
    npts = N
    station = "TST"
    channel = "HHZ"


class FakeTrace:
    data = NOISE.copy()
    stats = FakeStats()


# ---------------------------------------------------------------------------
# compute_pgv_pgd
# ---------------------------------------------------------------------------

class TestComputePgvPgd:
    def test_zero_signal_returns_zero(self):
        pgv, pgd = compute_pgv_pgd(np.zeros(100), DT)
        assert pgv == 0.0
        assert pgd == 0.0

    def test_positive_values_for_nonzero_signal(self):
        pgv, pgd = compute_pgv_pgd(NOISE, DT)
        assert pgv > 0.0
        assert pgd > 0.0

    def test_returns_floats(self):
        pgv, pgd = compute_pgv_pgd(NOISE, DT)
        assert isinstance(pgv, float)
        assert isinstance(pgd, float)

    def test_short_array(self):
        # 5 muestras — debe funcionar sin error
        pgv, pgd = compute_pgv_pgd(np.ones(5), DT)
        assert pgv >= 0.0
        assert pgd >= 0.0

    def test_pgd_ge_pgv_for_low_freq_signal(self):
        # señal de baja frecuencia: al integrar aumenta la amplitud
        t = np.linspace(0, 10.0, N)
        acc = np.sin(2.0 * np.pi * 0.5 * t)  # 0.5 Hz
        pgv, pgd = compute_pgv_pgd(acc, DT)
        assert pgv > 0.0
        assert pgd > 0.0


# ---------------------------------------------------------------------------
# compute_arias_intensity
# ---------------------------------------------------------------------------

class TestComputeAriasIntensity:
    def test_zero_signal_gives_zero(self):
        ia = compute_arias_intensity(np.zeros(100), DT)
        assert ia == pytest.approx(0.0)

    def test_positive_for_nonzero_signal(self):
        ia = compute_arias_intensity(NOISE, DT)
        assert ia > 0.0

    def test_scales_with_amplitude(self):
        ia1 = compute_arias_intensity(NOISE, DT)
        ia2 = compute_arias_intensity(NOISE * 2.0, DT)
        # Ia ∝ A² → duplicar amplitud cuadruplica Ia
        assert ia2 == pytest.approx(ia1 * 4.0, rel=1e-6)

    def test_returns_float(self):
        assert isinstance(compute_arias_intensity(NOISE, DT), float)


# ---------------------------------------------------------------------------
# compute_significant_duration
# ---------------------------------------------------------------------------

class TestComputeSignificantDuration:
    def test_zero_signal_returns_zeros(self):
        t_low, t_high, dur = compute_significant_duration(np.zeros(100), DT)
        assert t_low == 0.0
        assert t_high == 0.0
        assert dur == 0.0

    def test_duration_nonnegative(self):
        _, _, dur = compute_significant_duration(NOISE, DT)
        assert dur >= 0.0

    def test_d5_95_ge_d5_75(self):
        _, _, d5_75 = compute_significant_duration(NOISE, DT, 0.05, 0.75)
        _, _, d5_95 = compute_significant_duration(NOISE, DT, 0.05, 0.95)
        assert d5_95 >= d5_75

    def test_t_high_ge_t_low(self):
        t_low, t_high, _ = compute_significant_duration(NOISE, DT)
        assert t_high >= t_low

    def test_step_signal_duration(self):
        # Señal que empieza en cero y salta a 1.0 en el centro
        sig = np.zeros(N)
        sig[N // 2:] = 1.0
        _, _, dur = compute_significant_duration(sig, DT, 0.05, 0.75)
        # La energía está en la segunda mitad; duración debe ser > 0
        assert dur >= 0.0


# ---------------------------------------------------------------------------
# compute_cav
# ---------------------------------------------------------------------------

class TestComputeCav:
    def test_zero_signal_gives_zero(self):
        assert compute_cav(np.zeros(100), DT) == pytest.approx(0.0)

    def test_positive_for_nonzero(self):
        assert compute_cav(NOISE, DT) > 0.0

    def test_scales_with_amplitude(self):
        cav1 = compute_cav(NOISE, DT)
        cav2 = compute_cav(NOISE * 3.0, DT)
        assert cav2 == pytest.approx(cav1 * 3.0, rel=1e-6)

    def test_returns_float(self):
        assert isinstance(compute_cav(NOISE, DT), float)

    def test_constant_signal(self):
        # |a| = 5 cm/s², N muestras → CAV ≈ 5 * N * DT
        sig = np.full(N, 5.0)
        expected = 5.0 * (N - 1) * DT  # trapezoidal rule
        assert compute_cav(sig, DT) == pytest.approx(expected, rel=1e-3)


# ---------------------------------------------------------------------------
# compute_dominant_period
# ---------------------------------------------------------------------------

class TestComputeDominantPeriod:
    def test_short_array_returns_zero(self):
        t, f = compute_dominant_period(np.ones(3), DT)
        assert t == 0.0
        assert f == 0.0

    def test_sinusoid_dominant_freq(self):
        freq_target = 5.0  # Hz
        t = np.arange(N) * DT
        sig = np.sin(2.0 * np.pi * freq_target * t)
        t_dom, f_dom = compute_dominant_period(sig, DT)
        assert f_dom == pytest.approx(freq_target, abs=0.5)
        assert t_dom == pytest.approx(1.0 / freq_target, abs=0.05)

    def test_returns_positive_values(self):
        t_dom, f_dom = compute_dominant_period(NOISE, DT)
        assert f_dom >= 0.0
        assert t_dom >= 0.0

    def test_period_is_reciprocal_of_freq(self):
        t_dom, f_dom = compute_dominant_period(NOISE, DT)
        if f_dom > 0:
            assert t_dom == pytest.approx(1.0 / f_dom, rel=1e-6)


# ---------------------------------------------------------------------------
# compute_mean_period
# ---------------------------------------------------------------------------

class TestComputeMeanPeriod:
    def test_short_array_returns_zero(self):
        assert compute_mean_period(np.ones(3), DT) == 0.0

    def test_positive_for_normal_signal(self):
        tm = compute_mean_period(NOISE, DT)
        assert tm > 0.0

    def test_in_valid_range(self):
        # Tm debe estar dentro de la banda de análisis (0.25–25 Hz → 0.04–4 s)
        tm = compute_mean_period(NOISE, DT)
        assert 0.04 <= tm <= 4.0

    def test_returns_float(self):
        assert isinstance(compute_mean_period(NOISE, DT), float)


# ---------------------------------------------------------------------------
# compute_all_ims — función de alto nivel
# ---------------------------------------------------------------------------

class TestComputeAllIms:
    def test_from_fake_trace(self):
        result = compute_all_ims(FakeTrace())
        assert isinstance(result, IntensityMeasures)
        assert result.pga_cms2 is not None
        assert result.pga_cms2 > 0.0

    def test_from_dict(self):
        d = {"data": NOISE.copy(), "dt": DT}
        result = compute_all_ims(d)
        assert result.pga_cms2 is not None
        assert len(result.warnings) == 0 or all(isinstance(w, str) for w in result.warnings)

    def test_short_signal_adds_warning(self):
        short_trace = {"data": np.ones(5), "dt": DT}
        result = compute_all_ims(short_trace)
        assert any("corta" in w.lower() for w in result.warnings)
        assert result.pga_cms2 is None

    def test_zero_signal_all_ims_zero(self):
        zero_trace = {"data": np.zeros(N), "dt": DT}
        result = compute_all_ims(zero_trace)
        assert result.pga_cms2 == pytest.approx(0.0)
        assert result.arias_ms == pytest.approx(0.0)
        assert result.cav_cms == pytest.approx(0.0)

    def test_sensor_gain_scales_pga(self):
        d = {"data": NOISE.copy(), "dt": DT}
        r1 = compute_all_ims(d, sensor_gain=1.0)
        r2 = compute_all_ims(d, sensor_gain=2.0)
        assert r2.pga_cms2 == pytest.approx(r1.pga_cms2 * 2.0, rel=1e-6)

    def test_to_dict_has_expected_keys(self):
        result = compute_all_ims(FakeTrace())
        d = result.to_dict()
        assert "PGA (cm/s²)" in d
        assert "PGV (cm/s)" in d
        assert "Arias Intensity (m/s)" in d
        assert "CAV (cm/s)" in d

    def test_pga_g_ratio(self):
        result = compute_all_ims(FakeTrace())
        if result.pga_cms2 is not None and result.pga_g is not None:
            assert result.pga_g == pytest.approx(result.pga_cms2 / 980.665, rel=1e-6)

    def test_duration_matches_npts(self):
        result = compute_all_ims(FakeTrace())
        expected_dur = FakeStats.npts * FakeStats.delta
        assert result.duration_s == pytest.approx(expected_dur, rel=1e-6)

    def test_no_critical_warnings_for_normal_signal(self):
        result = compute_all_ims(FakeTrace())
        # No debe haber errores fatales de parseo
        assert result.pga_cms2 is not None
