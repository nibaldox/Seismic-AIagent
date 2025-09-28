"""Dependencias comunes para la API."""

from __future__ import annotations

from fastapi import Depends

from src.services.waveform_service import WaveformAnalysisService, WaveformServiceConfig

from .config import ApiSettings, get_settings


def _create_waveform_service(settings: ApiSettings) -> WaveformAnalysisService:
    config = WaveformServiceConfig(
        max_suggestions=settings.waveform_max_suggestions,
        sta=settings.waveform_sta,
        lta=settings.waveform_lta,
        on=settings.waveform_on,
        off=settings.waveform_off,
    )
    return WaveformAnalysisService(config)


_waveform_service: WaveformAnalysisService | None = None


def get_waveform_service(
    settings: ApiSettings = Depends(get_settings),
) -> WaveformAnalysisService:
    """Entrega una instancia singleton del servicio de waveforms."""

    global _waveform_service
    if _waveform_service is None:
        _waveform_service = _create_waveform_service(settings)
    return _waveform_service


def reset_waveform_service() -> None:
    """Permite re-crear la instancia cacheada (útil para pruebas)."""

    global _waveform_service
    _waveform_service = None
