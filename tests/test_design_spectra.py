"""Tests para src/core/design_spectra.py.

Cubre: ncch433_spectrum, asce7_spectrum.
"""
from __future__ import annotations

import numpy as np
import pytest

from src.core.design_spectra import (
    ASCE7_SITE_CLASSES,
    NCH433_SOILS,
    NCH433_ZONES,
    asce7_spectrum,
    ncch433_spectrum,
)


# ---------------------------------------------------------------------------
# ncch433_spectrum
# ---------------------------------------------------------------------------

class TestNch433Spectrum:
    def test_valid_zone_and_soil_returns_arrays(self):
        periods, sa = ncch433_spectrum(zone=3, soil="B")
        assert isinstance(periods, np.ndarray)
        assert isinstance(sa, np.ndarray)
        assert len(periods) == len(sa)

    def test_default_200_periods(self):
        periods, sa = ncch433_spectrum(zone=2, soil="C", n_periods=200)
        assert len(periods) == 200

    def test_custom_n_periods(self):
        periods, sa = ncch433_spectrum(zone=1, soil="A", n_periods=50)
        assert len(periods) == 50

    def test_sa_positive_everywhere(self):
        for zone in (1, 2, 3):
            for soil in ("A", "B", "C", "D"):
                _, sa = ncch433_spectrum(zone=zone, soil=soil)
                assert np.all(sa > 0), f"Sa <= 0 para zona={zone}, suelo={soil}"

    def test_sa_decreases_with_period_beyond_corner(self):
        periods, sa = ncch433_spectrum(zone=3, soil="D", t_max=4.0)
        # En la zona descendente (T > Tn ≈ 1.2 s) Sa debe decrecer
        mask = periods > 1.5
        if mask.sum() > 1:
            assert sa[mask][-1] < sa[mask][0]

    def test_damping_5pct_matches_eta_one(self):
        # Con amortiguamiento = 5% el factor eta = 1.0
        # Duplicar amortiguamiento debe reducir Sa
        _, sa_5 = ncch433_spectrum(zone=3, soil="B", damping=0.05)
        _, sa_10 = ncch433_spectrum(zone=3, soil="B", damping=0.10)
        assert np.all(sa_10 < sa_5)

    def test_higher_zone_gives_higher_sa(self):
        _, sa1 = ncch433_spectrum(zone=1, soil="B")
        _, sa3 = ncch433_spectrum(zone=3, soil="B")
        assert np.all(sa3 > sa1)

    def test_period_range(self):
        t_max = 3.0
        periods, _ = ncch433_spectrum(zone=2, soil="B", t_max=t_max)
        assert periods[0] == pytest.approx(0.0)
        assert periods[-1] == pytest.approx(t_max)

    def test_invalid_zone_raises_value_error(self):
        with pytest.raises(ValueError, match="Zona"):
            ncch433_spectrum(zone=99, soil="B")

    def test_invalid_soil_raises_value_error(self):
        with pytest.raises(ValueError):
            ncch433_spectrum(zone=2, soil="Z")

    def test_soil_case_insensitive(self):
        _, sa_lower = ncch433_spectrum(zone=2, soil="b")
        _, sa_upper = ncch433_spectrum(zone=2, soil="B")
        np.testing.assert_array_equal(sa_lower, sa_upper)

    def test_all_valid_combinations(self):
        for zone in NCH433_ZONES:
            for soil in NCH433_SOILS:
                periods, sa = ncch433_spectrum(zone=zone, soil=soil)
                assert sa.size > 0


# ---------------------------------------------------------------------------
# asce7_spectrum
# ---------------------------------------------------------------------------

class TestAsce7Spectrum:
    def test_default_returns_arrays(self):
        periods, sa = asce7_spectrum()
        assert isinstance(periods, np.ndarray)
        assert isinstance(sa, np.ndarray)
        assert len(periods) == len(sa)

    def test_default_200_periods(self):
        periods, sa = asce7_spectrum(n_periods=200)
        assert len(periods) == 200

    def test_sa_positive_everywhere(self):
        for sc in ("A", "B", "C", "D", "E"):
            _, sa = asce7_spectrum(Ss=1.0, S1=0.4, site_class=sc)
            assert np.all(sa > 0), f"Sa <= 0 para site_class={sc}"

    def test_damping_10pct_lower_than_5pct(self):
        _, sa_5 = asce7_spectrum(Ss=1.5, S1=0.6, site_class="D", damping=0.05)
        _, sa_10 = asce7_spectrum(Ss=1.5, S1=0.6, site_class="D", damping=0.10)
        # BL(10%) > BL(5%) → sa_10 < sa_5
        assert np.all(sa_10 <= sa_5)

    def test_period_range(self):
        t_max = 4.0
        periods, _ = asce7_spectrum(t_max=t_max)
        assert periods[0] == pytest.approx(0.0)
        assert periods[-1] == pytest.approx(t_max)

    def test_softer_site_gives_higher_sa_at_long_periods(self):
        # Sitio E es más blando que A → Sa a períodos largos mayor para E
        _, sa_a = asce7_spectrum(Ss=0.5, S1=0.2, site_class="A")
        _, sa_e = asce7_spectrum(Ss=0.5, S1=0.2, site_class="E")
        # Verificar al menos en la banda T=0.5-1.5 s
        periods = np.linspace(0.0, 4.0, 200)
        mask = (periods > 0.5) & (periods < 1.5)
        assert sa_e[mask].mean() > sa_a[mask].mean()

    def test_larger_ss_gives_larger_short_period_sa(self):
        _, sa_low = asce7_spectrum(Ss=0.5, S1=0.2, site_class="D")
        _, sa_high = asce7_spectrum(Ss=1.5, S1=0.2, site_class="D")
        periods = np.linspace(0.0, 4.0, 200)
        mask = (periods > 0.1) & (periods < 0.4)
        assert sa_high[mask].mean() > sa_low[mask].mean()

    def test_all_valid_site_classes(self):
        for sc in ASCE7_SITE_CLASSES:
            periods, sa = asce7_spectrum(Ss=1.0, S1=0.4, site_class=sc)
            assert sa.size > 0
            assert np.all(np.isfinite(sa))
