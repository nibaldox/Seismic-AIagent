"""Espectro de respuesta RotD50 / RotD100.

Implementa el método estándar PEER (Boore, 2010):
  - Rota las dos componentes horizontales de 0° a 180° en pasos de 1°.
  - Calcula Sa(T) para cada ángulo.
  - RotD50 = mediana de Sa en todos los ángulos.
  - RotD100 = máximo de Sa en todos los ángulos.

Referencia
----------
Boore, D.M. (2010). Orientation-independent, nongeometric-mean measures of
seismic intensity from two horizontal components of motion.
BSSA 100(4):1830-1835.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Tuple

import numpy as np

LOGGER = logging.getLogger(__name__)

try:
    from scipy import signal as _scipy_signal

    _SCIPY_OK = True
except ImportError:
    _SCIPY_OK = False


# ---------------------------------------------------------------------------
# Resultado
# ---------------------------------------------------------------------------

@dataclass
class RotDResult:
    """Resultado del cálculo RotD50/RotD100."""

    periods: np.ndarray          # [s]
    rotd50:  np.ndarray          # Sa RotD50 [cm/s²]
    rotd100: np.ndarray          # Sa RotD100 [cm/s²]
    damping: float               # fracción (p.ej. 0.05)
    comp1_id: str = ""           # ID de la componente 1
    comp2_id: str = ""           # ID de la componente 2
    angles_deg: np.ndarray = field(default_factory=lambda: np.arange(0, 181, 1, dtype=float))
    # Sa por ángulo: shape (n_angles, n_periods) — opcional, grande
    sa_matrix: np.ndarray | None = None


# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------

def compute_rotd(
    acc1: np.ndarray,
    acc2: np.ndarray,
    dt: float,
    *,
    damping: float = 0.05,
    t_min: float = 0.01,
    t_max: float = 4.0,
    n_periods: int = 100,
    angle_step_deg: float = 1.0,
    store_matrix: bool = False,
    comp1_id: str = "",
    comp2_id: str = "",
) -> RotDResult:
    """Calcula RotD50 y RotD100 para dos componentes horizontales.

    Args:
        acc1:          Aceleración componente 1 [cm/s²], array 1-D.
        acc2:          Aceleración componente 2 [cm/s²], array 1-D.
        dt:            Paso de tiempo [s].
        damping:       Amortiguamiento crítico (0.05 = 5 %).
        t_min:         Período mínimo [s].
        t_max:         Período máximo [s].
        n_periods:     Número de períodos en la grilla (escala log).
        angle_step_deg: Paso angular [°] entre 0 y 180.
        store_matrix:  Si True, guarda la matriz Sa(ángulo, período).
        comp1_id:      Nombre/ID de la componente 1 (para etiquetas).
        comp2_id:      Nombre/ID de la componente 2.

    Returns:
        RotDResult con periods, rotd50, rotd100 en cm/s².
    """
    if not _SCIPY_OK:
        raise ImportError("scipy es necesario para RotD50. Instala con: pip install scipy")

    acc1 = np.asarray(acc1, dtype=float)
    acc2 = np.asarray(acc2, dtype=float)
    n = min(len(acc1), len(acc2))
    acc1, acc2 = acc1[:n], acc2[:n]
    t_vec = np.arange(n) * dt

    periods = np.logspace(np.log10(t_min), np.log10(t_max), n_periods)
    angles = np.arange(0.0, 180.0 + angle_step_deg * 0.5, angle_step_deg)
    angles_rad = np.deg2rad(angles)

    n_ang = len(angles)
    sa_mat = np.zeros((n_ang, n_periods), dtype=float)

    for j, T in enumerate(periods):
        omega = 2.0 * np.pi / T
        c_damp = 2.0 * damping * omega
        k_spring = omega ** 2
        sys = _scipy_signal.lti([0, 0, k_spring], [1, c_damp, k_spring])
        t_out = t_vec

        # Sa de la componente 1
        try:
            _, r1 = _scipy_signal.lsim(sys, acc1, t_out)
            sa1 = float(np.max(np.abs(r1)))
        except Exception as exc:
            LOGGER.warning("lsim falló para comp1 T=%.3fs: %s — usando max abs como fallback", T, exc)
            sa1 = float(np.max(np.abs(acc1)))

        # Sa de la componente 2
        try:
            _, r2 = _scipy_signal.lsim(sys, acc2, t_out)
            sa2 = float(np.max(np.abs(r2)))
        except Exception as exc:
            LOGGER.warning("lsim falló para comp2 T=%.3fs: %s — usando max abs como fallback", T, exc)
            sa2 = float(np.max(np.abs(acc2)))

        # Proyección a cada ángulo: a_theta = a1*cos(θ) + a2*sin(θ)
        # Sa(θ) = max|disp_theta| * omega²
        try:
            _, resp1_full = _scipy_signal.lsim(sys, acc1, t_out)
            _, resp2_full = _scipy_signal.lsim(sys, acc2, t_out)
        except Exception as exc:
            LOGGER.warning("lsim falló para proyección angular T=%.3fs: %s — usando señal original", T, exc)
            resp1_full = acc1.copy()
            resp2_full = acc2.copy()

        for i, theta in enumerate(angles_rad):
            proj = resp1_full * np.cos(theta) + resp2_full * np.sin(theta)
            sa_mat[i, j] = float(np.max(np.abs(proj)))

    rotd50 = np.median(sa_mat, axis=0)
    rotd100 = np.max(sa_mat, axis=0)

    return RotDResult(
        periods=periods,
        rotd50=rotd50,
        rotd100=rotd100,
        damping=damping,
        comp1_id=comp1_id,
        comp2_id=comp2_id,
        angles_deg=angles,
        sa_matrix=sa_mat if store_matrix else None,
    )
