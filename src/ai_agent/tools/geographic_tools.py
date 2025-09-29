"""Geographic utility tools for the AI agent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import requests

from src.utils.logger import setup_logger
from .base import Tool

LOGGER = setup_logger(__name__)


@dataclass
class GeographicAnalysisTools(Tool):
    """Retrieve basic geological context and fault data."""

    context_endpoint: str
    faults_endpoint: str

    name: str = "geographic_context"
    description: str = "Return nearby geological context and active faults"

    def run(self, lat: float, lon: float, radius_km: int = 100) -> Dict[str, List[str]]:
        context = self._get_json(self.context_endpoint, lat=lat, lon=lon, radius=radius_km)
        faults = self._get_json(self.faults_endpoint, lat=lat, lon=lon, radius=radius_km)
        return {
            "geology": context.get("descriptions", []),
            "faults": faults.get("faults", []),
        }

    def _get_json(self, endpoint: str, **params):
        if not endpoint:
            return {}
        try:
            response = requests.get(endpoint, params=params, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as exc:  # pragma: no cover
            LOGGER.error("Failed to fetch geographic data: %s", exc)
            return {}
