"""Tests for FastAPI server module."""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from src.server import app, _datasets


@pytest.fixture
def client() -> Generator:
    _datasets.clear()
    with TestClient(app) as c:
        yield c


class TestHealth:
    def test_health_endpoint(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["version"] == "2.0.0"

    def test_health_with_datasets(self, client):
        _datasets["test"] = {"filename": "test.ms"}
        r = client.get("/api/health")
        assert r.json()["datasets"] == 1


class TestDatasets:
    def test_list_datasets_empty(self, client):
        r = client.get("/api/datasets")
        assert r.status_code == 200
        assert r.json()["datasets"] == []

    def test_list_datasets_with_data(self, client):
        _datasets["a.ms"] = {"traces": []}
        _datasets["b.ms"] = {"traces": []}
        r = client.get("/api/datasets")
        assert len(r.json()["datasets"]) == 2

    def test_get_dataset_not_found(self, client):
        r = client.get("/api/datasets/nonexistent")
        assert r.status_code == 404

    def test_get_dataset_found(self, client):
        _datasets["test.ms"] = {"filename": "test.ms", "traces": []}
        r = client.get("/api/datasets/test.ms")
        assert r.status_code == 200
        assert r.json()["filename"] == "test.ms"


class TestAnalyze:
    def test_analyze_no_file(self, client):
        r = client.post("/api/analyze")
        assert r.status_code in (422, 400)

    def test_analyze_empty_file(self, client):
        r = client.post("/api/analyze", files={"file": ("empty.ms", b"", "application/octet-stream")})
        assert r.status_code in (400, 422, 500)

    def test_analyze_unknown_format(self, client):
        r = client.post("/api/analyze", files={"file": ("test.xyz", b"test data", "application/octet-stream")})
        assert r.status_code == 422

    def test_analyze_wrong_data(self, client):
        r = client.post("/api/analyze", files={"file": ("test.ms", b"not actual miniseed data", "application/octet-stream")})
        assert r.status_code == 422


class TestLocation:
    def test_location_demo(self, client):
        r = client.get("/api/location/demo")
        assert r.status_code == 200
        data = r.json()
        assert "latitude" in data
        assert "depth_km" in data
        assert "magnitude" in data
        assert data["depth_km"] == 12.3
        assert len(data["traces"]) == 4

    def test_location_demo_has_summary(self, client):
        r = client.get("/api/location/demo")
        assert "summary" in r.json()


class TestWaveform:
    def test_waveform_not_found(self, client):
        r = client.get("/api/datasets/nonexistent/waveform")
        assert r.status_code == 404

    def test_waveform_trace_out_of_range(self, client):
        _datasets["test.ms"] = {"traces": [{"station": "ACE"}]}
        r = client.get("/api/datasets/test.ms/waveform?trace_idx=5")
        assert r.status_code == 404

    def test_waveform_found(self, client):
        _datasets["test.ms"] = {
            "traces": [
                {"station": "ACE01", "channel": "HNE", "sampling_rate": 100, "n_samples": 1000}
            ]
        }
        r = client.get("/api/datasets/test.ms/waveform?trace_idx=0")
        assert r.status_code == 200
        assert r.json()["station"] == "ACE01"


class TestSpectrum:
    def test_spectrum_not_found(self, client):
        r = client.get("/api/datasets/nonexistent/spectrum")
        assert r.status_code == 404

    def test_spectrum_types(self, client):
        _datasets["test.ms"] = {
            "traces": [
                {"station": "ACE01", "channel": "HNE", "sampling_rate": 100}
            ]
        }
        for stype in ["fft", "psd", "spectrogram", "hvsr", "rotd50"]:
            r = client.get(f"/api/datasets/test.ms/spectrum?type={stype}")
            assert r.status_code == 200
            assert len(r.json()["traces"]) == 1

    def test_spectrum_has_200_freq_points(self, client):
        _datasets["test.ms"] = {"traces": [{"station": "ACE01", "channel": "HNE", "sampling_rate": 100}]}
        r = client.get("/api/datasets/test.ms/spectrum?type=fft")
        assert len(r.json()["traces"][0]["freq"]) == 200


class TestFrontend:
    def test_frontend_index_served(self, client):
        r = client.get("/app/")
        assert r.status_code == 200
        assert "SeismoAnalyzer Pro" in r.text

    def test_frontend_css_served(self, client):
        r = client.get("/app/css/style.css")
        assert r.status_code == 200
        assert "--bg-deep" in r.text

    def test_frontend_js_served(self, client):
        r = client.get("/app/js/api.js")
        assert r.status_code == 200
        assert "API_BASE" in r.text

    def test_frontend_config_json(self, client):
        r = client.get("/app/config.json")
        assert r.status_code == 200
        data = r.json()
        assert "api_url" in data
