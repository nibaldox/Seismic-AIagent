"""Configuration utilities for SeismoAnalyzer Pro."""

from __future__ import annotations

import functools
from pathlib import Path
from typing import Any, Dict

import yaml

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_CONFIG_DIR = _PROJECT_ROOT / "config"


class ConfigError(RuntimeError):
    """Raised when a configuration file cannot be located or parsed."""


@functools.lru_cache(maxsize=None)
def load_yaml(relative_path: str) -> Dict[str, Any]:
    """Load a YAML config file from the config directory.

    Accepts either just the filename (e.g., "agno_config.yaml") or a path
    mistakenly prefixed with "config/". In the latter case, the redundant
    prefix is removed to avoid resolving to "config/config/...".
    """

    rp = Path(relative_path)
    # If absolute, use as-is; otherwise, normalize redundant leading 'config/'
    if not rp.is_absolute():
        parts = list(rp.parts)
        if parts and parts[0].lower() == "config":
            parts = parts[1:]  # drop redundant 'config' prefix
        rp = Path(*parts) if parts else rp
        config_path = _CONFIG_DIR / rp
    else:
        config_path = rp

    if not config_path.exists():
        raise ConfigError(
            f"Configuration file not found: {config_path} (hint: pase 'agno_config.yaml', no 'config/agno_config.yaml')"
        )

    with config_path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}
