"""Web search tool integrations."""

from __future__ import annotations

from dataclasses import dataclass
import importlib
from typing import List

try:  # pragma: no cover - optional dependency
    DDGS = importlib.import_module("duckduckgo_search").DDGS
except ModuleNotFoundError:  # pragma: no cover
    DDGS = None

from src.utils.logger import setup_logger
from .base import Tool

LOGGER = setup_logger(__name__)


@dataclass
class DuckDuckGoTools(Tool):
    """Perform DuckDuckGo web searches for contextual information."""

    name: str = "duckduckgo_search"
    description: str = "Search the web for recent seismic activity news"

    def run(self, query: str, *, max_results: int = 5) -> List[str]:
        if DDGS is None:  # pragma: no cover
            LOGGER.warning("duckduckgo-search not installed; returning empty results.")
            return []

        with DDGS() as search:
            results = search.text(query, max_results=max_results)
        return [f"{item['title']} – {item['href']}" for item in results]
