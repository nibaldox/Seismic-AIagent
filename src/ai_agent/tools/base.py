"""Common base classes for AI agent tools."""

from __future__ import annotations


class Tool:
    """Lightweight base class matching Agno's Tool interface."""

    name: str = "tool"
    description: str = ""

    def run(self, *args, **kwargs):  # pragma: no cover - interface placeholder
        raise NotImplementedError
