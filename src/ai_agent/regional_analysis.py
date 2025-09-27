"""Regional geological context helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import requests

from src.utils.logger import setup_logger

LOGGER = setup_logger(__name__)


@dataclass
class RegionalContext:
    description: str
    sources: Dict[str, str]


class RegionalAnalyzer:
    """Fetch ancillary geographic context for a location."""

    def __init__(self, *, geology_endpoint: Optional[str] = None) -> None:
        self.geology_endpoint = geology_endpoint

    def fetch_geology(self, lat: float, lon: float) -> Optional[str]:
        if not self.geology_endpoint:
            return None
        try:
            response = requests.get(
                self.geology_endpoint,
                params={"lat": lat, "lon": lon},
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("summary")
        except Exception as exc:  # pragma: no cover - network dependent
            LOGGER.error("Geology lookup failed: %s", exc)
            return None

    def build_context(self, lat: float, lon: float) -> RegionalContext:
        geology = self.fetch_geology(lat, lon)
        description = geology or "Geological context not available."
        sources = {"geology": self.geology_endpoint or "N/A"}
        return RegionalContext(description=description, sources=sources)
