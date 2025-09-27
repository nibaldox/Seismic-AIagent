"""Signal processing helpers: filtering and amplitude scaling."""

from __future__ import annotations

from typing import Iterable, Literal, Tuple

import numpy as np

try:  # pragma: no cover
    from obspy.signal.filter import bandpass as obspy_bandpass
except Exception:  # pragma: no cover
    obspy_bandpass = None  # type: ignore

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

    # Use ObsPy's bandpass & compose simple variants
    if filter_type == "bandpass":
        return obspy_bandpass(data, freqmin, freqmax, sampling_rate, corners=4, zerophase=True)
    if filter_type == "highpass":
        return obspy_bandpass(data, freqmin, sampling_rate / 2.0 - 1, sampling_rate, corners=4, zerophase=True)
    if filter_type == "lowpass":
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
