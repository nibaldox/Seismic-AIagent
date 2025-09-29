from __future__ import annotations

# --- Correlación catálogo ↔ picks ---
def correlacion_catalogo_picks(eventos: List[Dict[str, Any]], picks: List[Dict[str, Any]], ventana_s: float = 10.0) -> str:
    """
    Correlaciona eventos del catálogo con picks locales por matching temporal.
    Retorna resumen Markdown.
    """
    if not eventos or not picks:
        return "No hay eventos ni picks para correlacionar."
    lines = ["# Correlación catálogo ↔ picks", f"Ventana de matching: ±{ventana_s:.1f} s", ""]
    for ev in eventos:
        properties = ev.get("properties", {})
        ev_time = properties.get("time")
        ev_mag = properties.get("mag", "?")
        ev_place = properties.get("place", "?")
        if not ev_time:
            continue
        ev_dt = datetime.utcfromtimestamp(ev_time / 1000)
        matches = []
        for pk in picks:
            pk_time = pk.get("time_abs") or pk.get("time_rel")
            if pk_time is None:
                continue
            # Si pk_time es relativo, ignorar; si es absoluto, comparar
            if isinstance(pk_time, (int, float)):
                delta = abs((ev_time / 1000) - pk_time)
                if delta <= ventana_s:
                    matches.append(pk)
        if matches:
            lines.append(f"- Evento M{ev_mag} {ev_place} {ev_dt} correlacionado con {len(matches)} pick(s):")
            for pk in matches:
                phase = pk.get("phase", "?")
                station = pk.get("station", "?")
                channel = pk.get("channel", "?")
                lines.append(f"    - Pick {phase} {station}.{channel} t={pk.get('time_abs', pk.get('time_rel'))}")
        else:
            lines.append(f"- Evento M{ev_mag} {ev_place} {ev_dt} sin picks correlacionados.")
    return "\n".join(lines)
"""Utilities to search external earthquake catalogues."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.utils.logger import setup_logger

LOGGER = setup_logger(__name__)


@dataclass
class EarthquakeQuery:
    latitude: float
    longitude: float
    radius_km: int = 100
    days: int = 30
    min_magnitude: float = 2.5
    start: Optional[datetime] = None
    end: Optional[datetime] = None

    def to_usgs_params(self) -> Dict[str, Any]:
        # Prefer explicit start/end over relative window
        if self.start is not None and self.end is not None:
            starttime, endtime = self.start, self.end
        else:
            endtime = datetime.utcnow()
            starttime = endtime - timedelta(days=self.days)
        return {
            "format": "geojson",
            "latitude": self.latitude,
            "longitude": self.longitude,
            "maxradiuskm": self.radius_km,
            "starttime": starttime.strftime("%Y-%m-%d"),
            "endtime": endtime.strftime("%Y-%m-%d"),
            "minmagnitude": self.min_magnitude,
        }


class EarthquakeSearcher:
    """Search earthquakes from USGS and EMSC catalogues."""

    def __init__(
        self,
        usgs_url: str,
        emsc_url: str,
        *,
        timeout: int = 15,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        session: Optional[Session] = None,
        user_agent: str = "SeismoAnalyzer/1.0",
    ) -> None:
        self.usgs_url = usgs_url.rstrip("/") + "/query"
        self.emsc_url = emsc_url.rstrip("/") + "/query"
        self.timeout = timeout
        self.last_errors: Dict[str, str] = {}

        self.session = session or requests.Session()
        retry = Retry(
            total=max_retries,
            connect=max_retries,
            read=max_retries,
            status=max_retries,
            backoff_factor=backoff_factor,
            allowed_methods=["GET"],
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.session.headers.setdefault("User-Agent", user_agent)

    def _fetch(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        response = self.session.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def usgs_search(self, query: EarthquakeQuery) -> List[Dict[str, Any]]:
        data = self._fetch(self.usgs_url, params=query.to_usgs_params())
        return data.get("features", [])

    def emsc_search(self, query: EarthquakeQuery) -> List[Dict[str, Any]]:
        # EMSC focuses on Europe and Mediterranean region
        # Approximate coverage: 25degN-75degN, 15degW-45degE
        if not (25 <= query.latitude <= 75 and -15 <= query.longitude <= 45):
            raise ValueError(f"EMSC search not available for coordinates outside Europe/Mediterranean coverage (lat={query.latitude:.3f}, lon={query.longitude:.3f}). Use USGS for global coverage.")

        params = query.to_usgs_params()
        data = self._fetch(self.emsc_url, params=params)
        return data.get("features", [])

    def search_all(self, query: EarthquakeQuery) -> Dict[str, List[Dict[str, Any]]]:
        results: Dict[str, List[Dict[str, Any]]] = {}
        self.last_errors = {}
        try:
            results["usgs"] = self.usgs_search(query)
        except Exception as exc:  # pragma: no cover - network dependent
            LOGGER.error("USGS search failed: %s", exc)
            self.last_errors["usgs"] = str(exc)
        try:
            results["emsc"] = self.emsc_search(query)
        except Exception as exc:  # pragma: no cover
            LOGGER.error("EMSC search failed: %s", exc)
            self.last_errors["emsc"] = str(exc)
        return results

    @staticmethod
    def format_feature(feature: Dict[str, Any]) -> str:
        properties = feature.get("properties", {})
        magnitude = properties.get("mag", "?")
        place = properties.get("place", "Unknown location")
        time = properties.get("time")
        timestamp = datetime.utcfromtimestamp(time / 1000).isoformat() if time else "Unknown"
        return f"M{magnitude} - {place} at {timestamp} UTC"

    def summarize_results(self, results: Dict[str, List[Dict[str, Any]]]) -> str:
        lines: List[str] = []
        total_events = sum(len(features) for features in results.values())

        # Add summary header
        if total_events > 0:
            lines.append(f"**Total events found: {total_events}**\n")

        for source, features in results.items():
            lines.append(f"### {source.upper()} matches ({len(features)})")
            if not features:
                lines.append("- No events found.")
                if source in self.last_errors:
                    error_msg = self.last_errors[source]
                    if "EMSC search not available" in error_msg:
                        lines.append("> [info] EMSC only covers Europe/Mediterranean region. USGS provides global coverage.")
                    else:
                        lines.append(f"> [warning] ⚠️ {error_msg}")
                continue
            for feature in features[:5]:
                lines.append(f"- {self.format_feature(feature)}")
            remaining = max(0, len(features) - 5)
            if remaining:
                lines.append(f"- ... {remaining} additional events not shown.")
            if source in self.last_errors:
                lines.append(f"> [warning] ⚠️ {self.last_errors[source]}")
        return "\n".join(lines)
