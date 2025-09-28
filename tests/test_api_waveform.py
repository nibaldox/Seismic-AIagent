"""Pruebas para la API HTTP de waveforms."""

from __future__ import annotations

from typing import Iterable, List

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.dependencies import get_waveform_service, reset_waveform_service
from src.services import MagnitudeEstimate, PickSuggestion
from src.services.waveform_service import WaveformAnalysisService


class DummyWaveformService(WaveformAnalysisService):
    """Servicio doble que permite controlar las respuestas en pruebas."""

    def __init__(self) -> None:  # pragma: no cover - el init de la superclase no es necesario
        pass

    def suggest_picks(self, trace: object) -> List[PickSuggestion]:  # type: ignore[override]
        return [
            PickSuggestion(time_rel=1.2, score=2.5, phase="P"),
            PickSuggestion(time_rel=2.4, score=1.1, phase="S"),
        ]

    def estimate_magnitude_wood_anderson(
        self,
        *,
        picks: Iterable[PickPayload],
        trace: object,
    ) -> MagnitudeEstimate:  # type: ignore[override]
        return MagnitudeEstimate(
            ml=3.4,
            amplitude_mm=1.5,
            delta_ps=2.0,
            distance_km=12.0,
            notes="ok",
            warnings=["synthetic"],
        )

    def estimate_magnitude_placeholder(
        self,
        *,
        picks: Iterable[PickPayload],
        trace: object,
    ) -> MagnitudeEstimate:  # type: ignore[override]
        return MagnitudeEstimate(
            ml=2.7,
            amplitude_mm=0.9,
            delta_ps=1.8,
            distance_km=9.0,
            method="legacy",
        )


@pytest.fixture(autouse=True)
def override_service() -> Iterable[None]:
    reset_waveform_service()
    app.dependency_overrides[get_waveform_service] = lambda: DummyWaveformService()
    yield
    app.dependency_overrides.pop(get_waveform_service, None)
    reset_waveform_service()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health_endpoint_returns_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"


def test_pick_suggestions_endpoint(client: TestClient) -> None:
    response = client.post(
        "/waveform/picks/suggest",
        json={
            "waveform": {
                "samples": [0.0, 1.0, 0.0],
                "sampling_rate": 100.0,
                "station": "aaa",
                "channel": "hhz",
            }
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["suggestions"]) == 2
    assert payload["suggestions"][0]["phase"] == "P"


def test_magnitude_endpoint_wood_anderson(client: TestClient) -> None:
    picks = [
        {"phase": "P", "time_rel": 1.0, "station": "AAA", "channel": "HHZ"},
        {"phase": "S", "time_rel": 3.0, "station": "AAA", "channel": "HHZ"},
    ]
    response = client.post(
        "/waveform/magnitude",
        json={
            "waveform": {
                "samples": [0.0, 1.0, 0.0, 2.0],
                "sampling_rate": 50.0,
                "station": "AAA",
                "channel": "HHZ",
            },
            "picks": picks,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ml"] == pytest.approx(3.4)
    assert payload["warnings"] == ["synthetic"]


def test_magnitude_endpoint_legacy_algorithm(client: TestClient) -> None:
    picks = [
        {"phase": "P", "time_rel": 1.0, "station": "AAA", "channel": "HHZ"},
        {"phase": "S", "time_rel": 2.0, "station": "AAA", "channel": "HHZ"},
    ]
    response = client.post(
        "/waveform/magnitude",
        json={
            "waveform": {
                "samples": [0.0, 0.5, 0.1, 0.0],
                "sampling_rate": 40.0,
                "station": "AAA",
                "channel": "HHZ",
            },
            "picks": picks,
            "algorithm": "legacy",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["method"] == "legacy"
    assert payload["ml"] == pytest.approx(2.7)
