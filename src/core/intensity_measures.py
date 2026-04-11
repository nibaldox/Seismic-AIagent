"""Parámetros de intensidad sísmica (Intensity Measures — IMs).

Pipeline estándar V2: a partir de un acelerograma en unidades físicas (cm/s²)
calcula las métricas que todo informe geotécnico reporta, según estándares
COSMOS/PEER/CESMD.

Funciones principales
---------------------
compute_pgv_pgd(acc, dt)            → PGV [cm/s], PGD [cm]
compute_arias_intensity(acc, dt)    → Ia [m/s]
compute_significant_duration(...)   → D5-75, D5-95 [s]
compute_cav(acc, dt)                → CAV [cm/s]
compute_dominant_period(acc, dt)    → Tp [s]  (del pico del FAS)
compute_all_ims(trace)              → dict con todos los parámetros
"""

from __future__ import annotations

import numpy as _np_ver
# _trapz fue eliminado en NumPy 2.0; np.trapezoid es el nombre actual.
# El alias garantiza compatibilidad con NumPy >=1.x y >=2.0.
_trapz = getattr(_np_ver, "trapezoid", None) or getattr(_np_ver, "trapz", None)

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
_G_MS2 = 9.80665          # m/s²  (estándar IUPAC)
_G_CMS2 = 980.665         # cm/s²


# ---------------------------------------------------------------------------
# Dataclass de resultado
# ---------------------------------------------------------------------------

@dataclass
class IntensityMeasures:
    """Todos los IMs calculados para un acelerograma."""

    # --- Amplitudes pico ---
    pga_cms2: Optional[float] = None    # Peak Ground Acceleration [cm/s²]
    pga_g: Optional[float] = None       # PGA [g]
    pgv_cms: Optional[float] = None     # Peak Ground Velocity [cm/s]
    pgd_cm: Optional[float] = None      # Peak Ground Displacement [cm]

    # --- Energía e intensidad ---
    arias_ms: Optional[float] = None    # Arias Intensity [m/s]
    cav_cms: Optional[float] = None     # Cumulative Absolute Velocity [cm/s]

    # --- Duraciones significativas ---
    d5_75_s: Optional[float] = None     # Duración significativa 5-75 % Arias [s]
    d5_95_s: Optional[float] = None     # Duración significativa 5-95 % Arias [s]
    t5_s: Optional[float] = None        # Tiempo al 5 % de Arias [s]
    t75_s: Optional[float] = None       # Tiempo al 75 % de Arias [s]
    t95_s: Optional[float] = None       # Tiempo al 95 % de Arias [s]

    # --- Contenido frecuencial ---
    dominant_period_s: Optional[float] = None   # Periodo dominante Tp [s]
    dominant_freq_hz: Optional[float] = None    # Frecuencia dominante [Hz]
    mean_period_s: Optional[float] = None       # Tm (periodo medio espectral) [s]

    # --- Estadísticas básicas ---
    rms_cms2: Optional[float] = None    # RMS de la aceleración [cm/s²]
    duration_s: Optional[float] = None  # Duración total del registro [s]

    # --- Metadatos del cálculo ---
    units: str = "cm/s²"
    warnings: list = field(default_factory=list)

    def to_dict(self) -> Dict[str, Optional[float]]:
        """Retorna dict con nombre legible → valor (sin metadatos)."""
        return {
            "PGA (cm/s²)": self.pga_cms2,
            "PGA (g)": self.pga_g,
            "PGV (cm/s)": self.pgv_cms,
            "PGD (cm)": self.pgd_cm,
            "Arias Intensity (m/s)": self.arias_ms,
            "CAV (cm/s)": self.cav_cms,
            "D5-75 (s)": self.d5_75_s,
            "D5-95 (s)": self.d5_95_s,
            "T inicio 5% Arias (s)": self.t5_s,
            "T fin 75% Arias (s)": self.t75_s,
            "T fin 95% Arias (s)": self.t95_s,
            "Periodo dominante Tp (s)": self.dominant_period_s,
            "Frecuencia dominante (Hz)": self.dominant_freq_hz,
            "Periodo medio Tm (s)": self.mean_period_s,
            "RMS aceleración (cm/s²)": self.rms_cms2,
            "Duración (s)": self.duration_s,
        }


# ---------------------------------------------------------------------------
# Funciones de cálculo individual
# ---------------------------------------------------------------------------

def compute_pgv_pgd(
    acc: np.ndarray, dt: float
) -> Tuple[float, float]:
    """Calcula PGV y PGD mediante integración numérica trapezoidal.

    Args:
        acc: Acelerograma en cm/s².
        dt:  Intervalo de muestreo en segundos.

    Returns:
        (pgv_cms, pgd_cm)
    """
    acc = np.asarray(acc, dtype=float)
    vel = np.cumsum(acc) * dt          # integración rectangular (suficiente para cm/s²)
    disp = np.cumsum(vel) * dt
    pgv = float(np.max(np.abs(vel)))
    pgd = float(np.max(np.abs(disp)))
    return pgv, pgd


def compute_arias_intensity(
    acc: np.ndarray, dt: float
) -> float:
    """Arias Intensity: Ia = (π / 2g) × ∫₀ᵀ a²(t) dt  [m/s].

    Args:
        acc: Acelerograma en cm/s².
        dt:  Intervalo de muestreo en segundos.

    Returns:
        Ia en m/s.
    """
    acc_ms2 = np.asarray(acc, dtype=float) / 100.0   # cm/s² → m/s²
    ia = (np.pi / (2.0 * _G_MS2)) * _trapz(acc_ms2 ** 2, dx=dt)
    return float(ia)


def compute_significant_duration(
    acc: np.ndarray,
    dt: float,
    low: float = 0.05,
    high: float = 0.75,
) -> Tuple[float, float, float]:
    """Duración significativa entre umbrales de Arias Intensity.

    Args:
        acc:  Acelerograma en cm/s².
        dt:   Intervalo de muestreo en segundos.
        low:  Umbral inferior de Ia (default 5 %).
        high: Umbral superior de Ia (default 75 % → D5-75).

    Returns:
        (t_low [s], t_high [s], duration [s])
        donde duration = t_high − t_low.
    """
    acc_ms2 = np.asarray(acc, dtype=float) / 100.0
    arias_cum = np.cumsum(acc_ms2 ** 2) * dt * (np.pi / (2.0 * _G_MS2))
    ia_total = arias_cum[-1] if arias_cum.size > 0 else 0.0

    if ia_total <= 0:
        return 0.0, 0.0, 0.0

    times = np.arange(len(acc)) * dt
    i_low = int(np.searchsorted(arias_cum, low * ia_total))
    i_high = int(np.searchsorted(arias_cum, high * ia_total))
    i_low = min(i_low, len(times) - 1)
    i_high = min(i_high, len(times) - 1)

    t_low = float(times[i_low])
    t_high = float(times[i_high])
    return t_low, t_high, float(t_high - t_low)


def compute_cav(acc: np.ndarray, dt: float) -> float:
    """Cumulative Absolute Velocity: CAV = ∫₀ᵀ |a(t)| dt  [cm/s].

    Args:
        acc: Acelerograma en cm/s².
        dt:  Intervalo de muestreo en segundos.

    Returns:
        CAV en cm/s.
    """
    return float(_trapz(np.abs(np.asarray(acc, dtype=float)), dx=dt))


def compute_dominant_period(
    acc: np.ndarray, dt: float
) -> Tuple[float, float]:
    """Periodo y frecuencia dominante del espectro de Fourier (FAS).

    Args:
        acc: Acelerograma en cm/s².
        dt:  Intervalo de muestreo en segundos.

    Returns:
        (dominant_period_s, dominant_freq_hz)
    """
    acc = np.asarray(acc, dtype=float)
    n = acc.size
    if n < 4:
        return 0.0, 0.0

    win = np.hanning(n)
    spec = np.abs(np.fft.rfft(acc * win))
    freqs = np.fft.rfftfreq(n, d=dt)

    # Ignorar DC y frecuencias muy bajas (<0.05 Hz) para evitar artefactos de baseline
    mask = freqs > 0.05
    if not np.any(mask):
        return 0.0, 0.0

    dom_idx = int(np.argmax(spec[mask]))
    valid_freqs = freqs[mask]
    f_dom = float(valid_freqs[dom_idx])
    t_dom = 1.0 / f_dom if f_dom > 0 else 0.0
    return t_dom, f_dom


def compute_mean_period(acc: np.ndarray, dt: float) -> float:
    """Periodo medio espectral Tm (Rathje et al., 1998).

    Tm = Σ(Ci² / fi) / Σ(Ci²)   para 0.25 Hz ≤ fi ≤ 25 Hz.

    Args:
        acc: Acelerograma en cm/s².
        dt:  Intervalo de muestreo en segundos.

    Returns:
        Tm en segundos.
    """
    acc = np.asarray(acc, dtype=float)
    n = acc.size
    if n < 4:
        return 0.0

    spec = np.abs(np.fft.rfft(acc))
    freqs = np.fft.rfftfreq(n, d=dt)

    mask = (freqs >= 0.25) & (freqs <= 25.0)
    if not np.any(mask):
        return 0.0

    c2 = spec[mask] ** 2
    f = freqs[mask]
    denom = np.sum(c2)
    if denom <= 0:
        return 0.0
    return float(np.sum(c2 / f) / denom)


# ---------------------------------------------------------------------------
# Función de alto nivel
# ---------------------------------------------------------------------------

def compute_all_ims(
    trace,
    *,
    sensor_gain: float = 1.0,
    units_hint: str = "counts",
) -> IntensityMeasures:
    """Calcula todos los IMs para un ObsPy Trace o array numpy.

    Args:
        trace:       ObsPy Trace, o dict con claves 'data' y 'dt'.
        sensor_gain: Factor de conversión cuentas→cm/s². Por defecto 1.0
                     (asume que los datos ya están en unidades físicas).
        units_hint:  Etiqueta informativa de las unidades de entrada.

    Returns:
        IntensityMeasures con todos los parámetros calculados.
    """
    result = IntensityMeasures(units=units_hint)

    # --- Extraer datos y dt ---
    try:
        if hasattr(trace, "data") and hasattr(trace, "stats"):
            acc_raw = np.asarray(trace.data, dtype=float)
            dt = float(trace.stats.delta)
            sr = float(trace.stats.sampling_rate)
            result.duration_s = float(trace.stats.npts) * dt
        elif isinstance(trace, dict):
            acc_raw = np.asarray(trace["data"], dtype=float)
            dt = float(trace["dt"])
            sr = 1.0 / dt
            result.duration_s = len(acc_raw) * dt
        else:
            acc_raw = np.asarray(trace, dtype=float)
            dt = 0.01
            sr = 100.0
            result.duration_s = len(acc_raw) * dt
    except Exception as exc:
        result.warnings.append(f"No se pudo extraer datos: {exc}")
        return result

    if acc_raw.size < 10:
        result.warnings.append("Señal demasiado corta para calcular IMs.")
        return result

    # Aplicar ganancia si se proporcionó
    acc = acc_raw * sensor_gain

    # --- PGA ---
    try:
        result.pga_cms2 = float(np.max(np.abs(acc)))
        result.pga_g = result.pga_cms2 / _G_CMS2
        result.rms_cms2 = float(np.sqrt(np.mean(acc ** 2)))
    except Exception as exc:
        result.warnings.append(f"PGA: {exc}")

    # --- PGV / PGD ---
    try:
        result.pgv_cms, result.pgd_cm = compute_pgv_pgd(acc, dt)
    except Exception as exc:
        result.warnings.append(f"PGV/PGD: {exc}")

    # --- Arias Intensity ---
    try:
        result.arias_ms = compute_arias_intensity(acc, dt)
    except Exception as exc:
        result.warnings.append(f"Arias: {exc}")

    # --- Duraciones significativas ---
    try:
        t5, t75, d5_75 = compute_significant_duration(acc, dt, 0.05, 0.75)
        _, t95, d5_95 = compute_significant_duration(acc, dt, 0.05, 0.95)
        result.t5_s = t5
        result.t75_s = t75
        result.t95_s = t95
        result.d5_75_s = d5_75
        result.d5_95_s = d5_95
    except Exception as exc:
        result.warnings.append(f"Duración significativa: {exc}")

    # --- CAV ---
    try:
        result.cav_cms = compute_cav(acc, dt)
    except Exception as exc:
        result.warnings.append(f"CAV: {exc}")

    # --- Periodo / frecuencia dominante ---
    try:
        result.dominant_period_s, result.dominant_freq_hz = compute_dominant_period(acc, dt)
    except Exception as exc:
        result.warnings.append(f"Periodo dominante: {exc}")

    # --- Periodo medio Tm ---
    try:
        result.mean_period_s = compute_mean_period(acc, dt)
    except Exception as exc:
        result.warnings.append(f"Periodo medio: {exc}")

    return result
