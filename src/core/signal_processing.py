"""Signal processing helpers: filtering and amplitude scaling."""

from __future__ import annotations

from typing import Iterable, Literal, Tuple

import numpy as np

try:  # pragma: no cover
    from obspy.signal.filter import bandpass as obspy_bandpass
    from obspy.signal.filter import highpass as obspy_highpass
    from obspy.signal.filter import lowpass as obspy_lowpass
except Exception:  # pragma: no cover
    obspy_bandpass = None  # type: ignore
    obspy_highpass = None  # type: ignore
    obspy_lowpass = None  # type: ignore

FilterType = Literal["bandpass", "highpass", "lowpass", "none"]


def apply_filter(data: np.ndarray, sampling_rate: float, *, filter_type: FilterType, freqmin: float, freqmax: float) -> np.ndarray:
    """Apply a simple filter to a numpy array (does not modify original).

    Falls back to naive FFT filtering if ObsPy filter not available.
    """
    if filter_type == "none":
        return data
    if obspy_bandpass is None:
        # FFT crude filtering (very simple rectangular window)
        n = data.size
        if n == 0:
            return data
        freqs = np.fft.rfftfreq(n, d=1.0 / sampling_rate)
        spec = np.fft.rfft(data)
        mask = np.ones_like(freqs, dtype=bool)
        if filter_type in ("bandpass", "highpass"):
            mask &= freqs >= freqmin
        if filter_type in ("bandpass",):
            mask &= freqs <= freqmax
        if filter_type == "lowpass":
            mask &= freqs <= freqmax
        spec[~mask] = 0
        return np.fft.irfft(spec, n=n).astype(data.dtype)

    # Use ObsPy's dedicated filter functions
    if filter_type == "bandpass":
        return obspy_bandpass(data, freqmin, freqmax, sampling_rate, corners=4, zerophase=True)
    if filter_type == "highpass":
        if obspy_highpass is not None:
            return obspy_highpass(data, freqmin, sampling_rate, corners=4, zerophase=True)
        return obspy_bandpass(data, freqmin, sampling_rate * 0.45, sampling_rate, corners=4, zerophase=True)
    if filter_type == "lowpass":
        if obspy_lowpass is not None:
            return obspy_lowpass(data, freqmax, sampling_rate, corners=4, zerophase=True)
        return obspy_bandpass(data, 0.01, freqmax, sampling_rate, corners=4, zerophase=True)
    return data


def compute_global_range(traces: Iterable[np.ndarray]) -> Tuple[float, float]:
    mins = []
    maxs = []
    for arr in traces:
        if arr.size:
            mins.append(float(arr.min()))
            maxs.append(float(arr.max()))
    if not mins:
        return (0.0, 1.0)
    return (min(mins), max(maxs))


def normalize_trace(data: np.ndarray) -> np.ndarray:
    if data.size == 0:
        return data
    peak = np.max(np.abs(data))
    if peak == 0:
        return data
    return data / peak


# ---------------------------------------------------------------------------
# Corrección de línea de base (Baseline Correction — paso V1 estándar COSMOS)
# ---------------------------------------------------------------------------

def remove_baseline(
    data: np.ndarray,
    method: Literal["mean", "linear", "polynomial"] = "linear",
    poly_order: int = 2,
) -> np.ndarray:
    """Elimina la deriva de línea de base de un acelerograma.

    Métodos disponibles:
    - ``"mean"``       : resta la media (corrección orden 0).
    - ``"linear"``     : resta una tendencia lineal ajustada por mínimos cuadrados
                         (corrección orden 1, estándar más común).
    - ``"polynomial"`` : resta un polinomio de orden *poly_order* ajustado
                         (orden 2 para registros con deriva cuadrática).

    Args:
        data:       Array 1-D de la señal (acelerograma, velocidad, etc.).
        method:     Método de corrección.
        poly_order: Orden del polinomio (solo para ``method="polynomial"``).

    Returns:
        Array corregido del mismo tamaño que ``data``.
    """
    if data.size == 0:
        return data

    t = np.arange(data.size, dtype=float)

    if method == "mean":
        return data - np.mean(data)

    if method == "linear":
        coeffs = np.polyfit(t, data, 1)
        baseline = np.polyval(coeffs, t)
        return data - baseline

    if method == "polynomial":
        order = max(1, int(poly_order))
        coeffs = np.polyfit(t, data, order)
        baseline = np.polyval(coeffs, t)
        return data - baseline

    # Fallback: sin corrección
    return data
