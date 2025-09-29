"""Agent tools for querying seismic databases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import requests

from src.utils.logger import setup_logger
from .base import Tool

LOGGER = setup_logger(__name__)


@dataclass
class USGSTools(Tool):
    """Access the USGS earthquake API."""

    base_url: str

    name: str = "usgs_search"
    description: str = "Search USGS catalogue for recent earthquakes"

    def run(self, latitude: float, longitude: float, radius_km: int = 100, days: int = 30, min_magnitude: float = 2.5) -> List[Dict[str, Any]]:
        starttime = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
        params = {
            "format": "geojson",
            "latitude": latitude,
            "longitude": longitude,
            "maxradiuskm": radius_km,
            "starttime": starttime,
            "orderby": "time",
            "minmagnitude": min_magnitude,
        }
        response = requests.get(self.base_url.rstrip("/") + "/query", params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        return data.get("features", [])


@dataclass
class EMSCTools(Tool):
    """Access the EMSC earthquake API."""

    base_url: str

    name: str = "emsc_search"
    description: str = "Search EMSC catalogue for regional earthquakes"

    def run(self, latitude: float, longitude: float, radius_km: int = 100, days: int = 30, min_magnitude: float = 2.5) -> List[Dict[str, Any]]:
        starttime = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
        params = {
            "format": "geojson",
            "latitude": latitude,
            "longitude": longitude,
            "maxradiuskm": radius_km,
            "starttime": starttime,
            "minmagnitude": min_magnitude,
        }
        response = requests.get(self.base_url.rstrip("/") + "/query", params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        return data.get("features", [])
