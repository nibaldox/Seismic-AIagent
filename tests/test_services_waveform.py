"""Unit tests for the waveform service layer."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from src.services import PickPayload
from src.services.waveform_service import WaveformAnalysisService


class FakeTrace:
    """Minimal trace stub compatible with the core utilities."""

    def __init__(
        self,
        data: np.ndarray | list[float],
        *,
        sampling_rate: float = 100.0,
        station: str = "AAA",
        channel: str = "HHZ",
    ) -> None:
        self.data = np.asarray(data, dtype=float)
        self.stats = SimpleNamespace(
            sampling_rate=sampling_rate,
            station=station,
            channel=channel,
        )


def test_suggest_picks_wraps_core(monkeypatch: pytest.MonkeyPatch) -> None:
    service = WaveformAnalysisService()

    def fake_suggest(trace, **kwargs):  # type: ignore[unused-argument]
        return [
            {"time_rel": 1.25, "score": 3.5, "phase": "P"},
            {"time_rel": 2.00, "score": 1.2},
        ]

    monkeypatch.setattr("src.services.waveform_service.suggest_picks_sta_lta", fake_suggest)

    result = service.suggest_picks(FakeTrace([0, 1, 2, 3]))

    assert len(result) == 2
    assert result[0].time_rel == pytest.approx(1.25)
    assert result[0].method == "sta_lta"
    assert result[1].phase == "P?"


def test_estimate_magnitude_wood_anderson_returns_result() -> None:
    service = WaveformAnalysisService()
    pulse = np.zeros(5000)
    pulse[100:110] = np.linspace(0.0, 5.0, 10)
    pulse[110:120] = np.linspace(5.0, 0.0, 10)

    trace = FakeTrace(pulse)
    picks = [
        PickPayload(phase="P", time_rel=1.0, station="AAA", channel="HHZ"),
        PickPayload(phase="S", time_rel=3.0, station="AAA", channel="HHZ"),
    ]

    result = service.estimate_magnitude_wood_anderson(picks=picks, trace=trace)

    assert result.method == "wood_anderson"
    assert result.delta_ps == pytest.approx(2.0)
    assert result.warnings is not None


def test_estimate_magnitude_wood_anderson_requires_sampling_rate() -> None:
    service = WaveformAnalysisService()
    trace = FakeTrace([0.0, 1.0, 0.0], sampling_rate=0.0)
    picks = [
        PickPayload(phase="P", time_rel=1.0, station="AAA", channel="HHZ"),
        PickPayload(phase="S", time_rel=2.0, station="AAA", channel="HHZ"),
    ]

    with pytest.raises(ValueError):
        service.estimate_magnitude_wood_anderson(picks=picks, trace=trace)
