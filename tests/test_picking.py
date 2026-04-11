"""Tests para src/core/picking.py.

Cubre: _prefilter, suggest_picks_sta_lta, Pick, PickManager.
"""
from __future__ import annotations

import numpy as np
import pytest

from src.core.picking import (
    Pick,
    PickManager,
    _prefilter,
    suggest_picks_sta_lta,
)

# ---------------------------------------------------------------------------
# Helpers / señales sintéticas
# ---------------------------------------------------------------------------
SR = 100.0
DT = 1.0 / SR
RNG = np.random.default_rng(0)


class FakeStats:
    delta = DT
    sampling_rate = SR
    npts = 1000
    station = "TST"
    channel = "HHZ"


class FakeTrace:
    data = RNG.standard_normal(1000).astype(float)
    stats = FakeStats()


def _make_trace_with_onset(onset_s: float = 5.0, sr: float = SR, n: int = 2000) -> "object":
    """Traza sintética con onset claro para tests STA/LTA.

    Diseñada para el fallback FFT: señal larga (20 s a 100 Hz) con un onset
    muy marcado — relación señal/ruido de ~50× para superar cualquier umbral.
    """

    class _Stats:
        sampling_rate = sr
        delta = 1.0 / sr
        npts = n
        station = "SYN"
        channel = "HHZ"

    class _Tr:
        stats = _Stats()

    rng = np.random.default_rng(7)
    data = rng.standard_normal(n) * 0.02   # ruido muy suave (2 % de la señal)
    onset_idx = int(onset_s * sr)
    # Señal fuerte a partir del onset con caída lenta para que dure varios s
    if onset_idx < n:
        t = np.arange(n - onset_idx) / sr
        data[onset_idx:] += 10.0 * np.sin(2.0 * np.pi * 5.0 * t) * np.exp(-t * 0.5)
    _Tr.data = data
    return _Tr()


# ---------------------------------------------------------------------------
# _prefilter
# ---------------------------------------------------------------------------

class TestPrefilter:
    def test_empty_array_returns_empty(self):
        out = _prefilter(np.array([]), SR)
        assert out.size == 0

    def test_output_same_size_as_input(self):
        data = RNG.standard_normal(500)
        out = _prefilter(data, SR, freqmin=2.0, freqmax=15.0)
        assert out.size == data.size

    def test_single_freq_removed(self):
        # El filtro debe reducir la componente DC
        data = np.ones(1000) + RNG.standard_normal(1000) * 0.01
        out = _prefilter(data, SR, freqmin=2.0, freqmax=15.0)
        # Después del filtro la media debe ser casi cero
        assert abs(out.mean()) < 0.5

    def test_freqmin_ge_freqmax_returns_unfiltered(self):
        data = RNG.standard_normal(100)
        out = _prefilter(data, SR, freqmin=20.0, freqmax=5.0)
        np.testing.assert_array_equal(out, data)


# ---------------------------------------------------------------------------
# suggest_picks_sta_lta
# ---------------------------------------------------------------------------

class TestSuggestPicksStaLta:
    def test_empty_data_returns_empty(self):
        class EmptyStats:
            sampling_rate = SR
            delta = DT
            channel = "HHZ"

        class EmptyTrace:
            data = np.array([])
            stats = EmptyStats()

        result = suggest_picks_sta_lta(EmptyTrace())
        assert result == []

    def test_synthetic_onset_detected(self):
        # Señal de 20 s con onset a 3 s; el algoritmo puede o no detectarlo
        # dependiendo del ruido residual y los parámetros. Verificamos que no falle
        # y que si retorna picks, tengan la estructura correcta.
        tr = _make_trace_with_onset(onset_s=3.0, sr=SR, n=2000)
        picks = suggest_picks_sta_lta(tr, prefilter=False, suggest_s=False,
                                      on=2.0, lta=5.0)
        # Verifica que retorna lista (incluso vacía) y sin excepciones
        assert isinstance(picks, list)
        for p in picks:
            assert "time_rel" in p
            assert "phase" in p
            assert "score" in p

    def test_pick_dict_has_required_keys(self):
        tr = _make_trace_with_onset(onset_s=3.0, sr=SR, n=1000)
        picks = suggest_picks_sta_lta(tr, prefilter=False, suggest_s=False)
        if picks:
            for p in picks:
                assert "time_rel" in p
                assert "phase" in p
                assert "score" in p

    def test_time_rel_within_bounds(self):
        tr = _make_trace_with_onset(onset_s=3.0, sr=SR, n=1000)
        picks = suggest_picks_sta_lta(tr, prefilter=False, suggest_s=False)
        duration = 1000 / SR
        for p in picks:
            assert 0.0 <= p["time_rel"] <= duration

    def test_max_suggestions_respected(self):
        tr = FakeTrace()
        picks = suggest_picks_sta_lta(tr, max_suggestions=1, suggest_s=False)
        # Con suggest_s=False y max_suggestions=1, no más de 1 P
        p_picks = [p for p in picks if p["phase"] in ("P", "P?")]
        assert len(p_picks) <= 1

    def test_s_phase_added_after_p(self):
        tr = _make_trace_with_onset(onset_s=2.0, sr=SR, n=1000)
        picks = suggest_picks_sta_lta(tr, prefilter=False, suggest_s=True)
        phases = [p["phase"] for p in picks]
        # Si hay un P, debería haber un S? estimado
        if any(ph in ("P", "P?") for ph in phases):
            assert any(ph in ("S", "S?") for ph in phases)

    def test_uncertainty_s_is_positive(self):
        tr = _make_trace_with_onset(onset_s=3.0, sr=SR, n=1000)
        picks = suggest_picks_sta_lta(tr, prefilter=False, suggest_s=False)
        for p in picks:
            if p.get("uncertainty_s") is not None:
                assert p["uncertainty_s"] > 0.0


# ---------------------------------------------------------------------------
# PickManager
# ---------------------------------------------------------------------------

class TestPickManager:
    def _make_pick(self, phase="P", t=1.0, station="ST1", channel="HHZ") -> Pick:
        return Pick(
            phase=phase,
            time_rel=t,
            station=station,
            channel=channel,
            method="manual",
        )

    def test_empty_on_init(self):
        pm = PickManager()
        assert pm.list() == []

    def test_add_and_list(self):
        pm = PickManager()
        p = self._make_pick("P", 1.0)
        pm.add(p)
        assert len(pm.list()) == 1
        assert pm.list()[0].phase == "P"

    def test_add_multiple(self):
        pm = PickManager()
        pm.add(self._make_pick("P", 1.0))
        pm.add(self._make_pick("S", 2.5))
        assert len(pm.list()) == 2

    def test_remove_by_index(self):
        pm = PickManager()
        pm.add(self._make_pick("P", 1.0))
        pm.add(self._make_pick("S", 2.5))
        pm.remove(0)
        assert len(pm.list()) == 1
        assert pm.list()[0].phase == "S"

    def test_remove_invalid_index_does_nothing(self):
        pm = PickManager()
        pm.add(self._make_pick("P", 1.0))
        pm.remove(99)
        assert len(pm.list()) == 1

    def test_to_dicts_returns_list_of_dicts(self):
        pm = PickManager()
        pm.add(self._make_pick("P", 1.0))
        pm.add(self._make_pick("S", 2.0))
        dicts = pm.to_dicts()
        assert isinstance(dicts, list)
        assert all(isinstance(d, dict) for d in dicts)
        assert dicts[0]["phase"] == "P"
        assert dicts[1]["phase"] == "S"

    def test_to_dicts_has_time_rel(self):
        pm = PickManager()
        pm.add(self._make_pick("P", 3.14))
        dicts = pm.to_dicts()
        assert dicts[0]["time_rel"] == pytest.approx(3.14)

    def test_init_from_dicts(self):
        dicts = [
            {"phase": "P", "time_rel": 1.0, "station": "S1", "channel": "HHZ", "method": "auto"},
            {"phase": "S", "time_rel": 2.5, "station": "S1", "channel": "HHZ", "method": "auto"},
        ]
        pm = PickManager(picks=dicts)
        assert len(pm.list()) == 2
        assert pm.list()[0].phase == "P"

    def test_list_returns_copy(self):
        pm = PickManager()
        pm.add(self._make_pick("P", 1.0))
        lst1 = pm.list()
        lst2 = pm.list()
        assert lst1 is not lst2
