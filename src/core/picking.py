"""Basic phase picking utilities (MVP).

This module implements:
 - STA/LTA based simple pick suggestion.
 - In-memory PickManager to store picks inside Streamlit session (wrapped externally).

Design notes:
We assume picks are stored relative to the trace start (seconds) and also
optionally absolute (UTCDateTime) if trace has stats.starttime.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

import numpy as np

try:  # pragma: no cover - external optional dependency context
    from obspy.signal.trigger import classic_sta_lta, trigger_onset
except Exception:  # pragma: no cover - fallback lightweight implementation
    classic_sta_lta = None  # type: ignore
    trigger_onset = None  # type: ignore


@dataclass
class Pick:
    phase: str  # 'P' or 'S'
    time_rel: float  # seconds relative to trace start
    station: str
    channel: str
    method: str = "manual"
    time_abs: Optional[float] = None  # POSIX timestamp for portability
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


def suggest_picks_sta_lta(trace, *, sta: float = 1.0, lta: float = 10.0, on: float = 2.5, off: float = 1.0, max_suggestions: int = 3) -> List[Dict[str, Any]]:
    """Return simple STA/LTA based pick time suggestions (P-phase candidates).

    Returns list of dictionaries with keys: time_rel, phase (always 'P?'), score.
    """

    data = np.asarray(trace.data, dtype=float)
    if data.size == 0:
        return []

    sr = float(trace.stats.sampling_rate)
    nsta = max(1, int(sta * sr))
    nlta = max(nsta + 1, int(lta * sr))

    if classic_sta_lta is None or trigger_onset is None:
        # Fallback heuristic: use rolling RMS ratio
        # Short window RMS vs long window RMS
        if data.size < nlta:
            return []
        short = np.sqrt(np.maximum(np.convolve(data**2, np.ones(nsta) / nsta, mode="valid"), 0.0))
        long = np.sqrt(np.maximum(np.convolve(data**2, np.ones(nlta) / nlta, mode="valid"), 0.0))
        long = long[-short.size :]
        ratio = np.divide(short, long + 1e-9)
        indices = np.argwhere(ratio > on).ravel()
        times = indices / sr
        suggestions = []
        for t, r in zip(times[:max_suggestions], ratio[indices][:max_suggestions]):
            suggestions.append({"time_rel": float(t), "phase": "P?", "score": float(r)})
        return suggestions

    # Use ObsPy STA/LTA
    cft = classic_sta_lta(data, nsta, nlta)
    on_off = trigger_onset(cft, on, off)
    suggestions: List[Dict[str, Any]] = []
    for onset, _ in on_off[:max_suggestions]:
        t = onset / sr
        score = float(cft[onset]) if onset < len(cft) else 0.0
        suggestions.append({"time_rel": float(t), "phase": "P?", "score": score})
    return suggestions
