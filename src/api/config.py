"""Configuración para la API de servicios sísmicos."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiSettings(BaseSettings):
    """Valores configurables cargados desde el entorno."""

    app_name: str = "Seismic AI API"
    debug: bool = False

    waveform_max_suggestions: int = 3
    waveform_sta: float = 1.0
    waveform_lta: float = 10.0
    waveform_on: float = 2.5
    waveform_off: float = 1.0

    model_config = SettingsConfigDict(
        env_prefix="SEISMIC_API_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> ApiSettings:
    """Instancia cacheada de la configuración."""

    return ApiSettings()
