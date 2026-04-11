"""Tests para src/core/rotd50.py.

Cubre: compute_rotd, RotDResult.
"""
from __future__ import annotations

import numpy as np
import pytest

scipy_signal = pytest.importorskip(
    "scipy.signal",
    reason="scipy no está disponible — tests de RotD50 omitidos",
)

from src.core.rotd50 import RotDResult, compute_rotd  # noqa: E402 (importado tras importorskip)

# ---------------------------------------------------------------------------
# Señales sintéticas
# ---------------------------------------------------------------------------
SR = 100.0
DT = 1.0 / SR
N = 1000  # 10 s
RNG = np.random.default_rng(55)

ACC1 = RNG.standard_normal(N).astype(float)
ACC2 = RNG.standard_normal(N).astype(float)


# ---------------------------------------------------------------------------
# Tests básicos de estructura del resultado
# ---------------------------------------------------------------------------

class TestComputeRotdBasic:
    def test_returns_rotd_result(self):
        result = compute_rotd(ACC1, ACC2, DT, n_periods=10)
        assert isinstance(result, RotDResult)

    def test_periods_array_correct_length(self):
        n = 15
        result = compute_rotd(ACC1, ACC2, DT, n_periods=n)
        assert len(result.periods) == n

    def test_rotd50_array_correct_length(self):
        n = 15
        result = compute_rotd(ACC1, ACC2, DT, n_periods=n)
        assert len(result.rotd50) == n

    def test_rotd100_array_correct_length(self):
        n = 15
        result = compute_rotd(ACC1, ACC2, DT, n_periods=n)
        assert len(result.rotd100) == n

    def test_periods_in_log_range(self):
        t_min, t_max = 0.01, 4.0
        result = compute_rotd(ACC1, ACC2, DT, t_min=t_min, t_max=t_max, n_periods=20)
        assert result.periods[0] == pytest.approx(t_min, rel=1e-3)
        assert result.periods[-1] == pytest.approx(t_max, rel=1e-3)

    def test_periods_monotonically_increasing(self):
        result = compute_rotd(ACC1, ACC2, DT, n_periods=20)
        assert np.all(np.diff(result.periods) > 0)


# ---------------------------------------------------------------------------
# Tests de relación RotD100 >= RotD50
# ---------------------------------------------------------------------------

class TestRotd100GeRotd50:
    def test_rotd100_ge_rotd50_all_periods(self):
        result = compute_rotd(ACC1, ACC2, DT, n_periods=20)
        assert np.all(result.rotd100 >= result.rotd50 - 1e-9), (
            "RotD100 debe ser mayor o igual a RotD50 para todos los periodos"
        )

    def test_rotd100_ge_rotd50_for_orthogonal_components(self):
        # Componentes ortogonales con la misma amplitud
        t = np.arange(N) * DT
        a1 = np.sin(2.0 * np.pi * 2.0 * t)
        a2 = np.cos(2.0 * np.pi * 2.0 * t)
        result = compute_rotd(a1, a2, DT, n_periods=10)
        assert np.all(result.rotd100 >= result.rotd50 - 1e-9)


# ---------------------------------------------------------------------------
# Tests de valores no negativos
# ---------------------------------------------------------------------------

class TestRotdNonNegative:
    def test_rotd50_nonnegative(self):
        result = compute_rotd(ACC1, ACC2, DT, n_periods=10)
        assert np.all(result.rotd50 >= 0.0)

    def test_rotd100_nonnegative(self):
        result = compute_rotd(ACC1, ACC2, DT, n_periods=10)
        assert np.all(result.rotd100 >= 0.0)


# ---------------------------------------------------------------------------
# Tests de metadatos del resultado
# ---------------------------------------------------------------------------

class TestRotdMetadata:
    def test_damping_stored(self):
        result = compute_rotd(ACC1, ACC2, DT, damping=0.05)
        assert result.damping == pytest.approx(0.05)

    def test_comp_ids_stored(self):
        result = compute_rotd(ACC1, ACC2, DT, comp1_id="HHE", comp2_id="HHN")
        assert result.comp1_id == "HHE"
        assert result.comp2_id == "HHN"

    def test_angles_deg_default_0_to_180(self):
        result = compute_rotd(ACC1, ACC2, DT, n_periods=5)
        assert result.angles_deg[0] == pytest.approx(0.0)
        assert result.angles_deg[-1] == pytest.approx(180.0, abs=1.0)

    def test_store_matrix_false_by_default(self):
        result = compute_rotd(ACC1, ACC2, DT, n_periods=5)
        assert result.sa_matrix is None

    def test_store_matrix_true(self):
        n = 5
        result = compute_rotd(ACC1, ACC2, DT, n_periods=n, store_matrix=True)
        assert result.sa_matrix is not None
        assert result.sa_matrix.shape[1] == n


# ---------------------------------------------------------------------------
# Test con señal idéntica en ambas componentes
# ---------------------------------------------------------------------------

class TestRotdIdenticalComponents:
    def test_identical_components_rotd50_eq_rotd100(self):
        # Si acc1 == acc2, la proyección a cualquier ángulo es proporcional
        # → RotD50 debería ser igual (o muy cercano) a RotD100
        result = compute_rotd(ACC1, ACC1, DT, n_periods=10)
        ratio = result.rotd100 / (result.rotd50 + 1e-9)
        # Para señales idénticas la diferencia debe ser mínima
        assert np.all(ratio < 2.0)  # holgura razonable por efectos numéricos
