"""Waveform-focused service layer that wraps core seismic utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence

import numpy as np

from src.core.magnitude import (
    estimate_local_magnitude_placeholder,
    estimate_local_magnitude_wa,
)
from src.core.picking import suggest_picks_sta_lta
from .models import MagnitudeEstimate, PickPayload, PickSuggestion, TraceMetadata


@dataclass(slots=True)
class WaveformServiceConfig:
    """Configuration knobs for waveform analysis."""

    max_suggestions: int = 3
    sta: float = 1.0
    lta: float = 10.0
    on: float = 2.5
    off: float = 1.0


class WaveformAnalysisService:
    """Facade that exposes waveform-related business logic using typed contracts."""

    def __init__(self, config: WaveformServiceConfig | None = None):
        self._config = config or WaveformServiceConfig()

    # ------------------------------------------------------------------ picks
    def suggest_picks(self, trace: object) -> List[PickSuggestion]:
        """Return STA/LTA-based suggestions encoded as ``PickSuggestion`` models."""

        suggestions = suggest_picks_sta_lta(
            trace,
            sta=self._config.sta,
            lta=self._config.lta,
            on=self._config.on,
            off=self._config.off,
            max_suggestions=self._config.max_suggestions,
        )
        return [
            PickSuggestion(
                time_rel=s["time_rel"],
                score=max(float(s.get("score", 0.0)), 0.0),
                phase=s.get("phase", "P?"),
            )
            for s in suggestions
        ]

    # -------------------------------------------------------------- magnitudes
    def estimate_magnitude_wood_anderson(
        self,
        *,
        picks: Sequence[PickPayload],
        trace: object,
    ) -> MagnitudeEstimate:
        """Compute Wood-Anderson style ML using validated inputs."""

        metadata = self._build_metadata(trace)
        core_result = estimate_local_magnitude_wa(
            picks=_picks_to_dicts(picks),
            trace_data=_trace_to_numpy(trace),
            trace_sampling_rate=metadata.sampling_rate,
            station=metadata.station,
        )
        return MagnitudeEstimate.from_core(core_result)

    def estimate_magnitude_placeholder(
        self,
        *,
        picks: Sequence[PickPayload],
        trace: object,
    ) -> MagnitudeEstimate:
        """Legacy ML approximation for comparison purposes."""

        metadata = self._build_metadata(trace)
        core_result = estimate_local_magnitude_placeholder(
            picks=_picks_to_dicts(picks),
            trace_data=_trace_to_numpy(trace),
            trace_sampling_rate=metadata.sampling_rate,
            station=metadata.station,
        )
        return MagnitudeEstimate.from_core(core_result)

    # ------------------------------------------------------------- auxiliaries
    def _build_metadata(self, trace: object) -> TraceMetadata:
        stats = getattr(trace, "stats", None)
        if stats is None:
            raise ValueError("Trace does not contain stats metadata")
        sampling_rate = float(getattr(stats, "sampling_rate", 0.0))
        if sampling_rate <= 0:
            raise ValueError("Trace sampling rate must be greater than zero")
        station = getattr(stats, "station", "UNK") or "UNK"
        channel = getattr(stats, "channel", "CH") or "CH"
        return TraceMetadata(station=station, channel=channel, sampling_rate=sampling_rate)


def _trace_to_numpy(trace: object) -> np.ndarray:
    data = getattr(trace, "data", None)
    if data is None:
        raise ValueError("Trace has no data payload")
    array = np.asarray(data)
    if array.size == 0:
        raise ValueError("Trace data is empty")
    return array


def _picks_to_dicts(picks: Iterable[PickPayload]) -> List[dict]:
    return [pick.model_dump() for pick in picks]
