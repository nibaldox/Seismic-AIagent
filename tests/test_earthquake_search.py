"""Tests for earthquake search utilities."""

from __future__ import annotations

import requests

from src.ai_agent.earthquake_search import EarthquakeQuery, EarthquakeSearcher


class FakeResponse:
    def __init__(self, payload: dict, *, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"status={self.status_code}")

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, *results):
        self._results = list(results)
        self.calls = []
        self.headers = {}

    def mount(self, *_):  # pragma: no cover - not relevant for behaviour assertions
        return None

    def get(self, url, *, params=None, timeout=None):
        self.calls.append((url, params, timeout))
        if not self._results:
            raise RuntimeError("No more responses queued")
        result = self._results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

def test_search_all_records_errors():
    # Use coordinates in Rome (within EMSC coverage) to test actual network error
    query = EarthquakeQuery(latitude=41.9028, longitude=12.4964, radius_km=50, days=7)
    session = FakeSession(
        FakeResponse({"features": [{"properties": {"mag": 3.2, "place": "Test", "time": 1_000_000}}]}),
        Exception("EMSC offline"),
    )
    searcher = EarthquakeSearcher(
        "https://earthquake.usgs.gov/fdsnws/event/1/",
        "https://www.seismicportal.eu/fdsnws/event/1/",
        session=session,
        max_retries=0,
    )

    results = searcher.search_all(query)
    assert "usgs" in results
    assert results["usgs"]
    assert "emsc" not in results
    assert searcher.last_errors["emsc"] == "EMSC offline"

    summary = searcher.summarize_results({"USGS": [], "emsc": []})
    assert "⚠️" in summary


def test_summarize_results_limits_entries():
    query = EarthquakeQuery(latitude=0.0, longitude=0.0, radius_km=50, days=7)
    features = [
        {"properties": {"mag": i, "place": f"Zone {i}", "time": 1_000_000 + i * 1_000}}
        for i in range(7)
    ]
    session = FakeSession(FakeResponse({"features": features}))
    searcher = EarthquakeSearcher(
        "https://earthquake.usgs.gov/fdsnws/event/1/",
        "https://www.seismicportal.eu/fdsnws/event/1/",
        session=session,
        max_retries=0,
    )
    results = searcher.search_all(query)
    summary = searcher.summarize_results({"usgs": results.get("usgs", [])})
    assert "additional events" in summary