"""Phase picking utilities.

This module implements:
 - STA/LTA based pick suggestion with pre-filter and S-phase detection.
 - In-memory PickManager to store picks inside Streamlit session (wrapped externally).

Design notes:
Picks are stored relative to the trace start (seconds) and optionally absolute
(UTCDateTime) if trace has stats.starttime.

Pre-filtering (2-15 Hz bandpass) before STA/LTA suppresses long-period noise and
instrumental noise above 15 Hz that would otherwise generate false triggers.
S-phase detection uses the horizontal components (E/N/X/Y) where S energy is
dominant over P; on Z-only data it uses a secondary STA/LTA window after the
detected P-arrival.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

import numpy as np

try:  # pragma: no cover
    from obspy.signal.trigger import classic_sta_lta, trigger_onset
except Exception:  # pragma: no cover
    classic_sta_lta = None  # type: ignore
    trigger_onset = None  # type: ignore

try:  # pragma: no cover
    from obspy.signal.filter import bandpass as _obspy_bandpass
except Exception:  # pragma: no cover
    _obspy_bandpass = None  # type: ignore


def _prefilter(data: np.ndarray, sr: float, freqmin: float = 2.0, freqmax: float = 15.0) -> np.ndarray:
    """Apply a zerophase bandpass before STA/LTA to reduce false triggers.

    Falls back to an FFT brick-wall filter (less ideal but functional) when
    ObsPy is not available.
    """
    if data.size == 0:
        return data
    # Clamp freqmax to Nyquist
    nyq = sr * 0.45
    freqmax = min(freqmax, nyq)
    if freqmin >= freqmax:
        return data
    if _obspy_bandpass is not None:
        try:
            return _obspy_bandpass(data, freqmin, freqmax, sr, corners=4, zerophase=True)
        except Exception:
            pass
    # FFT fallback
    freqs = np.fft.rfftfreq(data.size, d=1.0 / sr)
    spec = np.fft.rfft(data)
    mask = (freqs >= freqmin) & (freqs <= freqmax)
    spec[~mask] = 0
    return np.fft.irfft(spec, n=data.size).astype(data.dtype)


@dataclass
class Pick:
    phase: str              # 'P', 'S', 'P?', 'S?'
    time_rel: float         # seconds relative to trace start
    station: str
    channel: str
    method: str = "manual"
    time_abs: Optional[float] = None   # POSIX timestamp for portability
    uncertainty_s: Optional[float] = None  # ±seconds (half-width of confidence interval)
    snr_db: Optional[float] = None         # local signal-to-noise at pick time
    extra: Dict[str, Any] = field(default_factory=dict)


class PickManager:
    """In-memory manager; caller persists externally (e.g., Streamlit session)."""

    def __init__(self, picks: Optional[List[Dict[str, Any]]] = None):
        self._picks: List[Pick] = []
        if picks:
            for d in picks:
                self._picks.append(Pick(**d))

    # -- CRUD -----------------------------------------------------------------
    def add(self, pick: Pick) -> None:
        self._picks.append(pick)

    def remove(self, index: int) -> None:
        if 0 <= index < len(self._picks):
            self._picks.pop(index)

    def list(self) -> List[Pick]:
        return list(self._picks)

    # -- Serialization --------------------------------------------------------
    def to_dicts(self) -> List[Dict[str, Any]]:
        return [p.__dict__.copy() for p in self._picks]


def _local_snr(data: np.ndarray, onset_idx: int, sr: float,
               noise_window_s: float = 2.0, signal_window_s: float = 1.0) -> Optional[float]:
    """Estimate SNR in dB at a pick onset using pre- and post-onset windows."""
    noise_samples = max(1, int(noise_window_s * sr))
    sig_samples = max(1, int(signal_window_s * sr))
    noise_start = max(0, onset_idx - noise_samples)
    noise_end = onset_idx
    sig_start = onset_idx
    sig_end = min(data.size, onset_idx + sig_samples)
    if noise_end <= noise_start or sig_end <= sig_start:
        return None
    noise_rms = float(np.sqrt(np.mean(data[noise_start:noise_end] ** 2)))
    sig_rms = float(np.sqrt(np.mean(data[sig_start:sig_end] ** 2)))
    if noise_rms <= 0:
        return None
    return float(20.0 * np.log10(sig_rms / noise_rms))


def suggest_picks_sta_lta(
    trace,
    *,
    sta: float = 0.5,
    lta: float = 10.0,
    on: float = 3.0,
    off: float = 1.0,
    max_suggestions: int = 3,
    prefilter: bool = True,
    freqmin: float = 2.0,
    freqmax: float = 15.0,
    suggest_s: bool = True,
) -> List[Dict[str, Any]]:
    """Return STA/LTA based pick suggestions for P (and optionally S) phases.

    Improvements over the original implementation:
    - Optional pre-filter (2–15 Hz bandpass) to suppress noise before STA/LTA.
    - Fallback uses proper index alignment (``mode='full'`` padding avoided).
    - Local SNR estimate at each onset.
    - Uncertainty estimate based on half the STA window length.
    - Rudimentary S-phase suggestion: if the channel is vertical (Z/3) and a P
      pick is found, proposes an S candidate at ~1.73×Δt after the last P (using
      Vp/Vs ≈ 1.73). For horizontal channels, runs an independent STA/LTA search
      after the P-window since S is dominant on horizontals.

    Returns list of dicts: time_rel, phase, score, uncertainty_s, snr_db.
    """
    data = np.asarray(trace.data, dtype=float)
    if data.size == 0:
        return []

    sr = float(trace.stats.sampling_rate)
    if sr <= 0:
        return []

    channel = str(getattr(getattr(trace, "stats", None), "channel", "")).upper()
    is_vertical = channel.endswith(("Z", "3"))

    # Pre-filter to seismic band before applying STA/LTA
    filtered = _prefilter(data, sr, freqmin, freqmax) if prefilter else data

    nsta = max(1, int(sta * sr))
    nlta = max(nsta + 1, int(lta * sr))
    uncertainty_s = sta / 2.0  # half STA window as timing uncertainty

    suggestions: List[Dict[str, Any]] = []

    if classic_sta_lta is None or trigger_onset is None:
        # Fallback: rolling RMS ratio with correct alignment
        if filtered.size < nlta:
            return []
        short = np.sqrt(np.maximum(
            np.convolve(filtered ** 2, np.ones(nsta) / nsta, mode="valid"), 0.0
        ))
        long_ = np.sqrt(np.maximum(
            np.convolve(filtered ** 2, np.ones(nlta) / nlta, mode="valid"), 0.0
        ))
        # Align: 'valid' output lengths differ by (nlta - nsta); trim long to short size
        min_len = min(short.size, long_.size)
        short = short[:min_len]
        long_ = long_[:min_len]
        ratio = np.divide(short, long_ + 1e-9)
        # Onset index offset caused by convolution padding
        offset = nlta - 1
        trigger_indices = np.argwhere(ratio > on).ravel()
        # Group consecutive triggers — take first of each burst
        p_onsets = []
        prev = -nlta
        for idx in trigger_indices:
            if idx - prev >= nlta:
                p_onsets.append(idx)
                prev = idx
        for onset_idx in p_onsets[:max_suggestions]:
            abs_idx = onset_idx + offset
            t = abs_idx / sr
            score = float(ratio[onset_idx])
            snr = _local_snr(filtered, abs_idx, sr)
            suggestions.append({
                "time_rel": t, "phase": "P?", "score": score,
                "uncertainty_s": uncertainty_s, "snr_db": snr,
            })
    else:
        # ObsPy STA/LTA
        cft = classic_sta_lta(filtered, nsta, nlta)
        on_off = trigger_onset(cft, on, off)
        for onset, _ in on_off[:max_suggestions]:
            t = float(onset) / sr
            score = float(cft[onset]) if onset < len(cft) else 0.0
            snr = _local_snr(filtered, onset, sr)
            suggestions.append({
                "time_rel": t, "phase": "P?", "score": score,
                "uncertainty_s": uncertainty_s, "snr_db": snr,
            })

    # --- S-phase suggestion ---
    if suggest_s and suggestions:
        last_p = suggestions[-1]
        p_time = last_p["time_rel"]

        if is_vertical:
            # Vp/Vs ≈ 1.73 → S arrives at p_time + p_time * (Vp/Vs - 1) ≈ p_time * 0.73
            # More practically: use Wadati relation Δts ≈ Δtp * (Vp/Vs - 1)
            # With Vp≈6, Vs≈3.5 → Vp/Vs≈1.71; ΔtS ≈ p_time * 0.71 (rough)
            s_time_estimate = p_time + p_time * 0.71
            if s_time_estimate < data.size / sr:
                suggestions.append({
                    "time_rel": s_time_estimate,
                    "phase": "S?",
                    "score": 0.0,  # estimated, not measured
                    "uncertainty_s": p_time * 0.15,  # ±15% of P-S interval
                    "snr_db": None,
                    "note": "Estimado por relación Vp/Vs=1.71 desde P. Verificar manualmente.",
                })
        else:
            # Horizontal channel: run independent STA/LTA starting after P
            p_start_idx = int(p_time * sr)
            h_data = filtered[p_start_idx:]
            if h_data.size >= nlta and (classic_sta_lta is not None):
                try:
                    cft_h = classic_sta_lta(h_data, nsta, nlta)
                    on_off_h = trigger_onset(cft_h, on * 0.8, off)
                    if on_off_h:
                        s_onset, _ = on_off_h[0]
                        s_time = p_time + float(s_onset) / sr
                        s_score = float(cft_h[s_onset]) if s_onset < len(cft_h) else 0.0
                        s_snr = _local_snr(h_data, s_onset, sr)
                        suggestions.append({
                            "time_rel": s_time, "phase": "S?", "score": s_score,
                            "uncertainty_s": uncertainty_s, "snr_db": s_snr,
                        })
                except Exception:
                    pass

    return suggestions
