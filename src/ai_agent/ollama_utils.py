"""Ollama_utils — Ollama local model profiles and health checking."""

from __future__ import annotations

import os
import socket
from typing import Optional

try:
    import requests
except ImportError:
    requests = None

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_TIMEOUT = 3.0


def check_ollama_available(host: str = OLLAMA_HOST, timeout: float = OLLAMA_TIMEOUT) -> bool:
    """Return True if Ollama is running and responding at the given host."""
    if requests is None:
        return False
    try:
        resp = requests.get(f"{host}/api/tags", timeout=timeout)
        return resp.status_code == 200
    except Exception:
        return False


def list_ollama_models(host: str = OLLAMA_HOST, timeout: float = OLLAMA_TIMEOUT) -> list[str]:
    """Return list of installed model names from Ollama."""
    if requests is None:
        return []
    try:
        resp = requests.get(f"{host}/api/tags", timeout=timeout)
        if resp.status_code != 200:
            return []
        return [m["name"] for m in resp.json().get("models", [])]
    except Exception:
        return []


TASK_MODEL_MAP = {
    "waveform_analysis": "mistral",
    "histogram_analysis": "mistral",
    "earthquake_search": "gemma2:2b",
    "phase_identification": "mistral",
    "magnitude_estimation": "mistral",
    "quality_assessment": "mistral",
    "code_generation": "codellama",
    "regional_analysis": "mistral",
    "seismic_interpretation": "mistral",
    "default": "llama3.2",
}


def get_task_model(task: str, available_models: Optional[list[str]] = None) -> Optional[str]:
    """Return the best Ollama model for a given task.

    If available_models is provided, verifies the model is actually installed
    before returning it. Falls back to 'llama3.2' if task model is not installed.
    Returns None if no suitable Ollama model is available.
    """
    preferred = TASK_MODEL_MAP.get(task, TASK_MODEL_MAP["default"])

    if available_models is not None:
        if preferred in available_models:
            return preferred
        for fallback in ("llama3.2", "mistral"):
            if fallback in available_models and fallback != preferred:
                return fallback
        return None

    return preferred


def get_ollama_host() -> str:
    return OLLAMA_HOST


def is_port_open(host: str = OLLAMA_HOST, timeout: float = 1.0) -> bool:
    """Check if the Ollama port is open (TCP connect test)."""
    try:
        _, port_str = host.rsplit(":", 1)
        port = int(port_str)
    except ValueError:
        port = 11434
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex(("localhost", port))
        sock.close()
        return result == 0
    except Exception:
        return False