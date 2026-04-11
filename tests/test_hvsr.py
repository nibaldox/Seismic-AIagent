"""Tests para src/core/hvsr.py.

Cubre: compute_hvsr, konno_ohmachi_smooth, SESAMECriteria, HVSRResult.
"""
from __future__ import annotations

import numpy as np
import pytest

from src.core.hvsr import HVSRResult, SESAMECriteria, compute_hvsr, konno_ohmachi_smooth

# ---------------------------------------------------------------------------
# Parámetros comunes
# ---------------------------------------------------------------------------
SR = 100.0
DT = 1.0 / SR
RNG = np.random.default_rng(99)

# 60 s de ruido blanco a 100 Hz — suficiente para ventanas de 20 s
N_LONG = int(60 * SR)
H1 = RNG.standard_normal(N_LONG).astype(float)
H2 = RNG.standard_normal(N_LONG).astype(float)
ZZ = RNG.standard_normal(N_LONG).astype(float) * 0.5  # vertical más silenciosa


# ---------------------------------------------------------------------------
# konno_ohmachi_smooth
# ---------------------------------------------------------------------------

class TestKonnoOhmachiSmooth:
    def test_output_same_shape(self):
        freqs = np.linspace(0.1, 25.0, 50)
        spec = np.abs(RNG.standard_normal(50)) + 0.01
        smoothed = konno_ohmachi_smooth(spec, freqs, b=40.0)
        assert smoothed.shape == spec.shape

    def test_nonnegative_output(self):
        freqs = np.linspace(0.5, 20.0, 40)
        spec = np.abs(RNG.standard_normal(40)) + 0.01
        smoothed = konno_ohmachi_smooth(spec, freqs)
        assert np.all(smoothed >= 0.0)

    def test_zero_freq_handled(self):
        freqs = np.array([0.0, 1.0, 5.0, 10.0])
        spec = np.array([0.0, 1.0, 2.0, 1.5])
        smoothed = konno_ohmachi_smooth(spec, freqs)
        assert smoothed.size == 4

    def test_flat_spectrum_preserved_approx(self):
        freqs = np.logspace(-1, 1.5, 60)
        spec = np.ones(60)
        smoothed = konno_ohmachi_smooth(spec, freqs)
        # Un espectro plano suavizado sigue siendo ~1
        assert np.all(smoothed[freqs > 0] >= 0.9)
        assert np.all(smoothed[freqs > 0] <= 1.1)


# ---------------------------------------------------------------------------
# compute_hvsr — señal demasiado corta
# ---------------------------------------------------------------------------

class TestComputeHvsrShortSignal:
    def test_signal_shorter_than_window_raises(self):
        short = RNG.standard_normal(100)  # 1 s a 100 Hz
        with pytest.raises(ValueError, match="corta|ventana|short|window"):
            compute_hvsr(short, short, short, DT, window_len_s=20.0)

    def test_win_samples_below_16_raises(self):
        # window_len_s = 0.05 s → 5 muestras → debe fallar
        data = RNG.standard_normal(N_LONG)
        with pytest.raises(ValueError):
            compute_hvsr(data, data, data, DT, window_len_s=0.05)


# ---------------------------------------------------------------------------
# compute_hvsr — señal sintética normal
# ---------------------------------------------------------------------------

class TestComputeHvsrNormal:
    def test_returns_hvsr_result(self):
        result = compute_hvsr(H1, H2, ZZ, DT, window_len_s=20.0)
        assert isinstance(result, HVSRResult)

    def test_f0_positive(self):
        result = compute_hvsr(H1, H2, ZZ, DT, window_len_s=20.0)
        assert result.f0_hz > 0.0

    def test_n_windows_positive(self):
        result = compute_hvsr(H1, H2, ZZ, DT, window_len_s=20.0)
        assert result.n_windows > 0

    def test_freqs_array_nonempty(self):
        result = compute_hvsr(H1, H2, ZZ, DT, window_len_s=20.0)
        assert result.freqs.size > 0

    def test_hv_mean_nonnegative(self):
        result = compute_hvsr(H1, H2, ZZ, DT, window_len_s=20.0)
        assert np.all(result.hv_mean >= 0.0)

    def test_hv_plus1_ge_hv_mean(self):
        result = compute_hvsr(H1, H2, ZZ, DT, window_len_s=20.0)
        assert np.all(result.hv_plus1 >= result.hv_mean - 1e-9)

    def test_hv_minus1_nonnegative(self):
        result = compute_hvsr(H1, H2, ZZ, DT, window_len_s=20.0)
        assert np.all(result.hv_minus1 >= 0.0)

    def test_t0_s_is_reciprocal_of_f0(self):
        result = compute_hvsr(H1, H2, ZZ, DT, window_len_s=20.0)
        assert result.t0_s == pytest.approx(1.0 / result.f0_hz, rel=1e-5)

    def test_sesame_criteria_are_booleans(self):
        result = compute_hvsr(H1, H2, ZZ, DT, window_len_s=20.0)
        sesame = result.sesame
        assert isinstance(sesame.c1_passed, bool)
        assert isinstance(sesame.c2_passed, bool)
        assert isinstance(sesame.c3_passed, bool)

    def test_store_windows_flag(self):
        result = compute_hvsr(H1, H2, ZZ, DT, window_len_s=20.0, store_windows=True)
        assert result.hv_windows is not None
        assert result.hv_windows.shape[0] == result.n_windows

    def test_no_store_windows_by_default(self):
        result = compute_hvsr(H1, H2, ZZ, DT, window_len_s=20.0)
        assert result.hv_windows is None

    def test_dominant_freq_in_requested_band(self):
        freq_min, freq_max = 0.1, 20.0
        result = compute_hvsr(H1, H2, ZZ, DT, window_len_s=20.0,
                              freq_min=freq_min, freq_max=freq_max)
        assert freq_min <= result.f0_hz <= freq_max


# ---------------------------------------------------------------------------
# SESAMECriteria
# ---------------------------------------------------------------------------

class TestSESAMECriteria:
    def test_all_passed_when_all_true(self):
        sc = SESAMECriteria(c1_passed=True, c2_passed=True, c3_passed=True)
        assert sc.all_passed is True

    def test_all_passed_false_when_any_false(self):
        sc = SESAMECriteria(c1_passed=True, c2_passed=False, c3_passed=True)
        assert sc.all_passed is False

    def test_summary_contains_status(self):
        sc = SESAMECriteria(c1_passed=True, c2_passed=True, c3_passed=True)
        summary = sc.summary
        assert isinstance(summary, str)
        assert len(summary) > 0
